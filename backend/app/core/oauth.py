"""
Google OAuth Module

Implements Google OAuth 2.0 flow for obtaining access tokens.
This is the same flow used by the Antigravity desktop app.
"""
import httpx
import time
import secrets
from typing import Optional
from pydantic import BaseModel

# Google OAuth Configuration (same as Antigravity desktop app)
CLIENT_ID = "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com"
CLIENT_SECRET = "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"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

# Required scopes for Gemini API access
SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/cclog",
    "https://www.googleapis.com/auth/experimentsandconfigs",
]


class TokenResponse(BaseModel):
    access_token: str
    expires_in: int
    token_type: str = "Bearer"
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


class UserInfo(BaseModel):
    email: str
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    
    def get_display_name(self) -> Optional[str]:
        if self.name and self.name.strip():
            return self.name
        if self.given_name or self.family_name:
            parts = [p for p in [self.given_name, self.family_name] if p]
            return " ".join(parts)
        return None


def generate_auth_url(redirect_uri: str, state: Optional[str] = None) -> str:
    """
    Generate the Google OAuth authorization URL.
    
    Args:
        redirect_uri: Where Google will redirect after authorization
        state: Optional state parameter for security
    
    Returns:
        The full authorization URL to redirect the user to
    """
    from urllib.parse import urlencode
    
    if state is None:
        state = secrets.token_urlsafe(32)
    
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    
    return f"{AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str, redirect_uri: str) -> TokenResponse:
    """
    Exchange an authorization code for access and refresh tokens.
    
    Args:
        code: The authorization code from Google's callback
        redirect_uri: The same redirect_uri used in the authorization request
    
    Returns:
        TokenResponse with access_token, refresh_token, etc.
    """
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(TOKEN_URL, data=data)
        
        if response.status_code == 200:
            json_data = response.json()
            return TokenResponse(**json_data)
        else:
            error_text = response.text
            raise Exception(f"Token exchange failed: {error_text}")


async def refresh_access_token(refresh_token: str) -> TokenResponse:
    """
    Use a refresh token to get a new access token.
    
    Args:
        refresh_token: The refresh token from a previous authorization
    
    Returns:
        TokenResponse with new access_token (refresh_token may be empty)
    """
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(TOKEN_URL, data=data)
        
        if response.status_code == 200:
            json_data = response.json()
            # Refresh response may not include refresh_token
            if "refresh_token" not in json_data:
                json_data["refresh_token"] = refresh_token
            return TokenResponse(**json_data)
        else:
            error_text = response.text
            raise Exception(f"Token refresh failed: {error_text}")


async def get_user_info(access_token: str) -> UserInfo:
    """
    Get the user's profile information using an access token.
    
    Args:
        access_token: A valid access token
    
    Returns:
        UserInfo with email, name, etc.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code == 200:
            return UserInfo(**response.json())
        else:
            error_text = response.text
            raise Exception(f"Failed to get user info: {error_text}")


async def fetch_account_info(access_token: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch the user's Google Cloud project ID and subscription tier from the cloudcode API.
    This is required for making API calls to Gemini.
    
    Uses loadCodeAssist endpoint (same as Rust implementation).
    
    Returns:
        Tuple of (project_id, subscription_tier) - either may be None
    """
    from typing import Tuple
    
    CLOUD_CODE_URL = "https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "antigravity/python/1.0",
    }
    
    payload = {
        "metadata": {
            "ideType": "ANTIGRAVITY"
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(CLOUD_CODE_URL, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                project_id = data.get("cloudaicompanionProject")
                
                # Extract subscription tier from paidTier or currentTier
                # Priority: paidTier > currentTier (same as Rust)
                subscription_tier = None
                paid_tier = data.get("paidTier")
                current_tier = data.get("currentTier")
                
                if paid_tier and paid_tier.get("id"):
                    subscription_tier = paid_tier.get("id")
                elif current_tier and current_tier.get("id"):
                    subscription_tier = current_tier.get("id")
                
                return (project_id, subscription_tier)
    except Exception as e:
        print(f"Failed to fetch account info: {e}")
    
    # Fallback to default project (works for most users)
    return ("bamboo-precept-lgxtn", None)


# Keep old function name for backwards compatibility
async def fetch_project_id(access_token: str) -> Optional[str]:
    """Legacy wrapper for fetch_account_info - returns only project_id."""
    project_id, _ = await fetch_account_info(access_token)
    return project_id
