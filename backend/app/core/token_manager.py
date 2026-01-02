"""
Token Manager

Manages a pool of accounts for API requests with:
- Round-robin account rotation
- 60-second time-window locking (prevents frequent switching)
- Automatic token refresh (5 minutes before expiry)
- Automatic project_id fetching
- 429 retry with account switching
"""
import asyncio
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from threading import Lock
from sqlmodel import Session, select

from app.core.database import engine
from app.core.oauth import refresh_access_token, fetch_account_info
from app.models.account import Account


@dataclass
class ProxyToken:
    """Token data for a single account."""
    account_id: str
    email: str
    access_token: str
    refresh_token: str
    expires_in: int
    expiry_timestamp: int
    project_id: Optional[str] = None
    subscription_tier: Optional[str] = None  # FREE/PRO/ULTRA
    average_quota: Optional[float] = None    # Cached avg quota for routing


class TokenManager:
    """
    Manages a pool of accounts for API request handling.
    
    Features:
    - Loads accounts from database
    - Round-robin rotation
    - 60-second sticky session (same account within time window)
    - Automatic token refresh before expiry
    - Account switching on 429 errors
    """
    
    def __init__(self):
        self._tokens: Dict[str, ProxyToken] = {}
        self._current_index: int = 0
        self._last_used: Optional[Tuple[str, float]] = None  # (account_id, timestamp)
        self._lock = Lock()
        self._refresh_lock = asyncio.Lock()
    
    async def load_accounts(self) -> int:
        """Load all accounts from database into memory pool."""
        with Session(engine) as session:
            accounts = session.exec(select(Account)).all()
            count = 0
            
            for acc in accounts:
                if acc.token and acc.token.access_token:
                    self._tokens[acc.id] = ProxyToken(
                        account_id=acc.id,
                        email=acc.email,
                        access_token=acc.token.access_token,
                        refresh_token=acc.token.refresh_token,
                        expires_in=acc.token.expires_in,
                        expiry_timestamp=acc.token.expiry_timestamp,
                        project_id=acc.token.project_id,
                        subscription_tier=acc.token.subscription_tier,
                        average_quota=acc.token.average_quota,
                    )
                    count += 1
            
            return count
    
    def reload_account(self, account_id: str) -> bool:
        """Reload a single account from database."""
        with Session(engine) as session:
            acc = session.get(Account, account_id)
            if acc and acc.token:
                self._tokens[acc.id] = ProxyToken(
                    account_id=acc.id,
                    email=acc.email,
                    access_token=acc.token.access_token,
                    refresh_token=acc.token.refresh_token,
                    expires_in=acc.token.expires_in,
                    expiry_timestamp=acc.token.expiry_timestamp,
                    project_id=acc.token.project_id,
                    subscription_tier=acc.token.subscription_tier,
                    average_quota=acc.token.average_quota,
                )
                return True
        return False
    
    @property
    def pool_size(self) -> int:
        """Number of accounts in pool."""
        return len(self._tokens)
    
    async def get_token(
        self, 
        quota_group: str = "gemini", 
        force_rotate: bool = False
    ) -> Tuple[str, str, str]:
        """
        Get a token for API requests.
        
        Args:
            quota_group: Type of request (gemini/claude/image_gen)
            force_rotate: Force switch to next account
        
        Returns:
            Tuple of (access_token, project_id, email)
        
        Raises:
            ValueError: If no accounts available
        """
        if not self._tokens:
            raise ValueError("Token pool is empty. Please add accounts first.")
        
        account_ids = list(self._tokens.keys())
        total = len(account_ids)
        
        # 1. Check 60-second time-window lock (sticky session)
        selected_token: Optional[ProxyToken] = None
        
        if not force_rotate and quota_group != "image_gen":
            if self._last_used:
                last_id, last_time = self._last_used
                if time.time() - last_time < 60:
                    if last_id in self._tokens:
                        selected_token = self._tokens[last_id]
                        # print(f"[TokenManager] 60s sticky: reusing {selected_token.email}")
        
        # 2. Smart Selection: Pick account with highest quota (or round-robin if no quota data)
        if selected_token is None:
            # For image generation, use all accounts (testing if FREE accounts have access)
            # Previously filtered to PRO/ULTRA only, but user wants to test FREE too
            if quota_group == "image_gen":
                all_tokens = list(self._tokens.values())
                if not all_tokens:
                    raise ValueError("No accounts available for image generation.")
                
                # Prefer PRO/ULTRA but include FREE in rotation
                pro_tokens = [
                    t for t in all_tokens
                    if t.subscription_tier and ('pro' in t.subscription_tier.lower() or 'ultra' in t.subscription_tier.lower())
                ]
                
                # If force_rotate, always round-robin through ALL accounts to test
                if force_rotate:
                    with self._lock:
                        idx = self._current_index % len(all_tokens)
                        self._current_index += 1
                    selected_token = all_tokens[idx]
                    tier = selected_token.subscription_tier or "unknown"
                    print(f"[TokenManager] Force rotate for image_gen: selected {selected_token.email} (tier={tier}, idx={idx}/{len(all_tokens)})")
                else:
                    # First try: prefer PRO/ULTRA with highest quota
                    if pro_tokens:
                        pro_with_quota = [t for t in pro_tokens if t.average_quota is not None and t.average_quota > 0.05]
                        if pro_with_quota:
                            pro_with_quota.sort(key=lambda t: t.average_quota or 0, reverse=True)
                            selected_token = pro_with_quota[0]
                        else:
                            with self._lock:
                                idx = self._current_index % len(pro_tokens)
                                self._current_index += 1
                            selected_token = pro_tokens[idx]
                    else:
                        # No PRO accounts, use any account
                        with self._lock:
                            idx = self._current_index % len(all_tokens)
                            self._current_index += 1
                        selected_token = all_tokens[idx]
            else:
                # Normal selection: Sort accounts by average_quota (descending), None values go last
                tokens_with_quota = [
                    t for t in self._tokens.values() 
                    if t.average_quota is not None and t.average_quota > 0.05
                ]
                
                if tokens_with_quota:
                    # Sort by quota descending
                    tokens_with_quota.sort(key=lambda t: t.average_quota or 0, reverse=True)
                    # Pick the best one (or round-robin among top 3 if similar)
                    if len(tokens_with_quota) >= 3:
                        top_quota = tokens_with_quota[0].average_quota or 0
                        similar = [t for t in tokens_with_quota[:3] if (t.average_quota or 0) >= top_quota * 0.9]
                        if len(similar) > 1:
                            # Round-robin among similar high-quota accounts
                            with self._lock:
                                idx = self._current_index % len(similar)
                                self._current_index += 1
                            selected_token = similar[idx]
                        else:
                            selected_token = tokens_with_quota[0]
                    else:
                        selected_token = tokens_with_quota[0]
                else:
                    # Fallback to round-robin if no quota data
                    with self._lock:
                        idx = self._current_index % total
                        self._current_index += 1
                    
                    account_id = account_ids[idx]
                    selected_token = self._tokens[account_id]
                
                # Update sticky session (except for image generation)
                self._last_used = (selected_token.account_id, time.time())
        
        # 3. Check if token needs refresh (5 minutes before expiry)
        now = int(time.time())
        if now >= selected_token.expiry_timestamp - 300:
            selected_token = await self._refresh_token(selected_token)
        
        # 4. Ensure project_id is available (and subscription_tier)
        if not selected_token.project_id:
            selected_token = await self._fetch_metadata(selected_token)
        
        return (
            selected_token.access_token,
            selected_token.project_id or "bamboo-precept-lgxtn",  # Use fallback project_id if None
            selected_token.email
        )
    
    async def rotate_on_error(self) -> Optional[Tuple[str, str, str]]:
        """Force rotation to next account after error (e.g., 429)."""
        if self.pool_size <= 1:
            return None
        return await self.get_token(force_rotate=True)
    
    async def _refresh_token(self, token: ProxyToken) -> ProxyToken:
        """Refresh an expiring token."""
        async with self._refresh_lock:
            # Double-check after acquiring lock
            now = int(time.time())
            if now < token.expiry_timestamp - 300:
                return token
            
            try:
                print(f"[TokenManager] Refreshing token for {token.email}...")
                new_token = await refresh_access_token(token.refresh_token)
                
                # Update in-memory token
                token.access_token = new_token.access_token
                token.expires_in = new_token.expires_in
                token.expiry_timestamp = now + new_token.expires_in
                
                # Update in database
                await self._save_token_to_db(token)
                
                print(f"[TokenManager] Token refreshed for {token.email}")
                return token
                
            except Exception as e:
                print(f"[TokenManager] Failed to refresh token for {token.email}: {e}")
                raise
    
    async def _fetch_metadata(self, token: ProxyToken) -> ProxyToken:
        """Fetch and save project_id and subscription_tier for an account."""
        try:
            print(f"[TokenManager] Fetching metadata for {token.email}...")
            project_id, subscription_tier = await fetch_account_info(token.access_token)
            
            token.project_id = project_id
            token.subscription_tier = subscription_tier
            
            # Update in database
            await self._save_metadata_to_db(token.account_id, project_id, subscription_tier)
            
            print(f"[TokenManager] Metadata for {token.email}: project={project_id}, tier={subscription_tier}")
            return token
            
        except Exception as e:
            print(f"[TokenManager] Failed to fetch metadata for {token.email}: {e}")
            # Use default project_id
            token.project_id = "bamboo-precept-lgxtn"
            return token
    
    async def _save_token_to_db(self, token: ProxyToken):
        """Save refreshed token to database."""
        with Session(engine) as session:
            acc = session.get(Account, token.account_id)
            if acc and acc.token:
                acc.token.access_token = token.access_token
                acc.token.expires_in = token.expires_in
                acc.token.expiry_timestamp = token.expiry_timestamp
                session.add(acc)
                session.commit()
    
    async def _save_metadata_to_db(self, account_id: str, project_id: str, subscription_tier: Optional[str]):
        """Save project_id and subscription_tier to database."""
        with Session(engine) as session:
            acc = session.get(Account, account_id)
            if acc and acc.token:
                acc.token.project_id = project_id
                if subscription_tier:
                    acc.token.subscription_tier = subscription_tier
                session.add(acc)
                session.commit()
    
    def get_all_accounts(self) -> List[dict]:
        """Get summary of all accounts in pool."""
        result = []
        for token in self._tokens.values():
            result.append({
                "account_id": token.account_id,
                "email": token.email,
                "project_id": token.project_id,
                "subscription_tier": token.subscription_tier,
                "average_quota": token.average_quota,
                "expiry_timestamp": token.expiry_timestamp,
                "expires_in_seconds": max(0, token.expiry_timestamp - int(time.time())),
            })
        return result
    
    async def refresh_all_expiring_tokens(self):
        """
        Proactively refresh all tokens that will expire within 5 minutes.
        Called by background scheduler.
        """
        now = int(time.time())
        refreshed = 0
        
        for token in list(self._tokens.values()):
            if now >= token.expiry_timestamp - 300:  # Within 5 minutes of expiry
                try:
                    await self._refresh_token(token)
                    refreshed += 1
                    print(f"[Scheduler] Refreshed token for {token.email}")
                except Exception as e:
                    print(f"[Scheduler] Failed to refresh {token.email}: {e}")
        
        if refreshed > 0:
            print(f"[Scheduler] Refreshed {refreshed} expiring tokens")
        
        return refreshed
    
    async def update_quotas(self):
        """
        Fetch and update average_quota for all accounts.
        Called by background scheduler every 10 minutes.
        """
        import httpx
        
        CLOUD_CODE_URL = "https://cloudcode-pa.googleapis.com/v1internal"
        GROUPS = {
            "claude_gpt": "claude-sonnet-4-5-thinking",
            "gemini_pro": "gemini-3-pro-high",
            "gemini_flash": "gemini-3-flash"
        }
        
        updated = 0
        
        for token in list(self._tokens.values()):
            # 0. Self-heal missing metadata (Subscription Tier)
            if not token.subscription_tier:
                try:
                    await self._fetch_metadata(token)
                except Exception as e:
                    print(f"[Scheduler] Failed to backfill metadata for {token.email}: {e}")

            try:
                headers = {
                    "Authorization": f"Bearer {token.access_token}",
                    "Content-Type": "application/json",
                    "User-Agent": "antigravity/python/1.0",
                }
                
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(
                        f"{CLOUD_CODE_URL}:fetchAvailableModels",
                        json={"project": token.project_id or ""},
                        headers=headers
                    )
                    
                    if response.status_code != 200:
                        continue
                    
                    data = response.json()
                    models = data.get("models", {})
                    
                    fractions = []
                    for group_key, model_name in GROUPS.items():
                        if model_name in models:
                            quota_info = models[model_name].get("quotaInfo", {})
                            remaining = quota_info.get("remainingFraction")
                            if remaining is not None:
                                fractions.append(remaining)
                    
                    if fractions:
                        avg = sum(fractions) / len(fractions)
                        token.average_quota = round(avg, 4)
                        
                        # Persist to database
                        await self._save_average_quota_to_db(token.account_id, token.average_quota)
                        updated += 1
                        
            except Exception as e:
                print(f"[Scheduler] Failed to update quota for {token.email}: {e}")
        
        if updated > 0:
            print(f"[Scheduler] Updated quotas for {updated} accounts")
        
        return updated
    
    async def _save_average_quota_to_db(self, account_id: str, average_quota: float):
        """Save average_quota to database."""
        with Session(engine) as session:
            acc = session.get(Account, account_id)
            if acc and acc.token:
                acc.token.average_quota = average_quota
                session.add(acc)
                session.commit()


# Global singleton instance
_token_manager: Optional[TokenManager] = None


def get_token_manager() -> TokenManager:
    """Get global TokenManager instance."""
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager


async def init_token_manager() -> int:
    """Initialize and load accounts into TokenManager."""
    manager = get_token_manager()
    count = await manager.load_accounts()
    print(f"[TokenManager] Loaded {count} accounts into pool")
    return count
