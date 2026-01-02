"""
Token Import API

Provides endpoints for importing tokens/accounts without OAuth.
This is essential for web deployments where OAuth callback isn't directly available.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session
from pydantic import BaseModel
from typing import List, Optional
import json
import time

from app.core.database import get_session
from app.models.account import Account, Token

router = APIRouter()


class TokenImport(BaseModel):
    """Schema for importing a single token."""
    email: str
    access_token: str
    refresh_token: str
    expires_in: int = 3600
    project_id: Optional[str] = None
    session_id: Optional[str] = None


class BulkImport(BaseModel):
    """Schema for bulk import."""
    accounts: List[TokenImport]


@router.post("/import-token")
def import_single_token(data: TokenImport, session: Session = Depends(get_session)):
    """
    Import a single account using raw token data.
    
    This is useful when:
    - User has exported token from Antigravity desktop app
    - User has obtained token through other means
    """
    # Generate account ID from email
    account_id = data.email.replace("@", "_at_").replace(".", "_")
    
    # Check if account already exists
    existing = session.get(Account, account_id)
    if existing:
        # Update existing token
        if existing.token:
            existing.token.access_token = data.access_token
            existing.token.refresh_token = data.refresh_token
            existing.token.expires_in = data.expires_in
            existing.token.expiry_timestamp = int(time.time()) + data.expires_in
            existing.token.project_id = data.project_id
        session.add(existing)
        session.commit()
        return {"status": "updated", "account_id": account_id}
    
    # Create new account
    token = Token(
        access_token=data.access_token,
        refresh_token=data.refresh_token,
        expires_in=data.expires_in,
        expiry_timestamp=int(time.time()) + data.expires_in,
        token_type="Bearer",
        email=data.email,
        project_id=data.project_id,
        session_id=data.session_id,
        account_id=account_id
    )
    
    account = Account(
        id=account_id,
        email=data.email,
        created_at=int(time.time()),
        last_used=int(time.time())
    )
    account.token = token
    
    session.add(account)
    session.commit()
    
    # Auto-reload TokenManager to include the new account
    from app.core.token_manager import get_token_manager
    import asyncio
    token_manager = get_token_manager()
    asyncio.create_task(token_manager.load_accounts())
    
    return {"status": "created", "account_id": account_id}


@router.post("/import-bulk")
def import_bulk_tokens(data: BulkImport, session: Session = Depends(get_session)):
    """Import multiple accounts at once."""
    results = []
    for item in data.accounts:
        try:
            result = import_single_token(item, session)
            results.append({"email": item.email, **result})
        except Exception as e:
            results.append({"email": item.email, "status": "error", "error": str(e)})
    
    return {"imported": len([r for r in results if r.get("status") != "error"]), "results": results}


@router.post("/import-json-file")
async def import_json_file(file: UploadFile = File(...), session: Session = Depends(get_session)):
    """
    Import accounts from a JSON file (e.g., exported from Antigravity desktop).
    
    Expected format:
    {
        "accounts": [
            {
                "email": "user@gmail.com",
                "token": {
                    "access_token": "...",
                    "refresh_token": "...",
                    ...
                }
            }
        ]
    }
    """
    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    
    accounts_data = data.get("accounts", [])
    if not accounts_data:
        raise HTTPException(status_code=400, detail="No accounts found in file")
    
    imported = 0
    errors = []
    
    for acc in accounts_data:
        try:
            email = acc.get("email", "")
            token_data = acc.get("token", {})
            
            if not email or not token_data.get("access_token"):
                continue
            
            import_data = TokenImport(
                email=email,
                access_token=token_data.get("access_token", ""),
                refresh_token=token_data.get("refresh_token", ""),
                expires_in=token_data.get("expires_in", 3600),
                project_id=token_data.get("project_id"),
                session_id=token_data.get("session_id")
            )
            import_single_token(import_data, session)
            imported += 1
        except Exception as e:
            errors.append({"email": acc.get("email", "unknown"), "error": str(e)})
    
    # Auto-reload TokenManager to include new accounts
    if imported > 0:
        from app.core.token_manager import get_token_manager
        import asyncio
        token_manager = get_token_manager()
        asyncio.create_task(token_manager.load_accounts())
    
    return {"imported": imported, "errors": errors}


@router.post("/import-antigravity-account")
def import_antigravity_account(data: dict, session: Session = Depends(get_session)):
    """
    Import a single account from Antigravity's account JSON format.
    
    This is the format stored in ~/.antigravity_tools/accounts/{id}.json
    
    Expected format (paste the entire account JSON):
    {
        "id": "uuid",
        "email": "user@gmail.com",
        "name": "User Name",
        "token": {
            "access_token": "ya29...",
            "refresh_token": "1//...",
            "expires_in": 3599,
            "expiry_timestamp": 1735500000,
            "token_type": "Bearer",
            "project_id": "...",
            "session_id": "..."
        },
        "quota": {...},
        "created_at": 1735400000,
        "last_used": 1735499000
    }
    """
    email = data.get("email")
    token_data = data.get("token", {})
    
    if not email:
        raise HTTPException(status_code=400, detail="Missing email field")
    if not token_data.get("access_token"):
        raise HTTPException(status_code=400, detail="Missing access_token in token field")
    
    import_data = TokenImport(
        email=email,
        access_token=token_data.get("access_token", ""),
        refresh_token=token_data.get("refresh_token", ""),
        expires_in=token_data.get("expires_in", 3600),
        project_id=token_data.get("project_id"),
        session_id=token_data.get("session_id")
    )
    
    result = import_single_token(import_data, session)
    return {"status": "success", "email": email, **result}
