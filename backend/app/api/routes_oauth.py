"""
OAuth API Routes

Provides endpoints for OAuth authorization flow.
Since this is a web service, we use a web-based OAuth flow instead of localhost callback.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlmodel import Session
from pydantic import BaseModel
from typing import Optional
import secrets
import time

from app.core.database import get_session
from app.core.oauth import (
    generate_auth_url,
    exchange_code,
    refresh_access_token,
    get_user_info,
    fetch_project_id,
    TokenResponse as OAuthTokenResponse,
)
from app.models.account import Account, Token

router = APIRouter()

# Store pending OAuth states (in production, use Redis or database)
_pending_states: dict = {}


class OAuthStartResponse(BaseModel):
    auth_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str


@router.get("/start")
async def start_oauth(request: Request) -> OAuthStartResponse:
    """
    Start the OAuth flow.
    
    Returns an authorization URL that the user should visit in their browser.
    The callback will be to this server's /api/oauth/callback endpoint.
    
    For web deployment, configure your domain in Google Cloud Console.
    """
    # Determine callback URL based on request
    host = request.headers.get("host", "localhost:8000")
    scheme = request.headers.get("x-forwarded-proto", "http")
    redirect_uri = f"{scheme}://{host}/api/oauth/callback"
    
    # Generate state for security
    state = secrets.token_urlsafe(32)
    _pending_states[state] = {
        "redirect_uri": redirect_uri,
        "created_at": time.time()
    }
    
    auth_url = generate_auth_url(redirect_uri, state)
    
    return OAuthStartResponse(auth_url=auth_url, state=state)


@router.get("/callback")
async def oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """
    OAuth callback endpoint.
    
    Google will redirect here after the user authorizes.
    """
    if error:
        return HTMLResponse(f"""
        <html>
            <head><title>OAuth Failed</title></head>
            <body>
                <h1>❌ OAuth Failed</h1>
                <p>Error: {error}</p>
                <p><a href="/">Return to home</a></p>
            </body>
        </html>
        """, status_code=400)
    
    if not code or not state:
        return HTMLResponse("""
        <html>
            <head><title>OAuth Failed</title></head>
            <body>
                <h1>❌ OAuth Failed</h1>
                <p>Missing code or state parameter</p>
            </body>
        </html>
        """, status_code=400)
    
    # Verify state
    if state not in _pending_states:
        return HTMLResponse("""
        <html>
            <head><title>OAuth Failed</title></head>
            <body>
                <h1>❌ OAuth Failed</h1>
                <p>Invalid or expired state. Please try again.</p>
            </body>
        </html>
        """, status_code=400)
    
    state_data = _pending_states.pop(state)
    redirect_uri = state_data["redirect_uri"]
    
    try:
        # Exchange code for tokens
        token_response = await exchange_code(code, redirect_uri)
        
        if not token_response.refresh_token:
            return HTMLResponse("""
            <html>
                <head><title>OAuth Warning</title></head>
                <body>
                    <h1>⚠️ OAuth Partial Success</h1>
                    <p>Google did not return a refresh token.</p>
                    <p>This usually happens if you've authorized before.</p>
                    <p>Please go to <a href="https://myaccount.google.com/permissions">Google Account Permissions</a>,
                       revoke access to this app, and try again.</p>
                </body>
            </html>
            """, status_code=400)
        
        # Get user info
        user_info = await get_user_info(token_response.access_token)
        
        # Fetch project_id (required for API calls)
        project_id = await fetch_project_id(token_response.access_token)
        
        # Save to database
        account_id = user_info.email.replace("@", "_at_").replace(".", "_")
        
        # Check if account exists
        existing = session.get(Account, account_id)
        if existing:
            # Update existing
            if existing.token:
                existing.token.access_token = token_response.access_token
                existing.token.refresh_token = token_response.refresh_token
                existing.token.expires_in = token_response.expires_in
                existing.token.expiry_timestamp = int(time.time()) + token_response.expires_in
                existing.token.project_id = project_id
            existing.name = user_info.get_display_name()
            existing.last_used = int(time.time())
            session.add(existing)
        else:
            # Create new
            token = Token(
                access_token=token_response.access_token,
                refresh_token=token_response.refresh_token,
                expires_in=token_response.expires_in,
                expiry_timestamp=int(time.time()) + token_response.expires_in,
                token_type="Bearer",
                email=user_info.email,
                project_id=project_id,
                account_id=account_id
            )
            account = Account(
                id=account_id,
                email=user_info.email,
                name=user_info.get_display_name(),
                created_at=int(time.time()),
                last_used=int(time.time())
            )
            account.token = token
            session.add(account)
        
        session.commit()
        
        # Auto-reload TokenManager to include the new account
        from app.core.token_manager import get_token_manager
        token_manager = get_token_manager()
        await token_manager.load_accounts()
        
        return HTMLResponse(f"""
        <html>
            <head>
                <title>OAuth Success</title>
                <style>
                    body {{ font-family: system-ui; max-width: 600px; margin: 50px auto; padding: 20px; }}
                    .success {{ color: #22c55e; }}
                    .token-info {{ background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <h1 class="success">✅ OAuth Success!</h1>
                <p>Account <strong>{user_info.email}</strong> has been added.</p>
                <div class="token-info">
                    <p><strong>Name:</strong> {user_info.get_display_name() or 'N/A'}</p>
                    <p><strong>Access Token:</strong> {token_response.access_token[:30]}...</p>
                    <p><strong>Refresh Token:</strong> {token_response.refresh_token[:20]}...</p>
                    <p><strong>Expires In:</strong> {token_response.expires_in} seconds</p>
                </div>
                <p>You can now close this window and use the API.</p>
            </body>
        </html>
        """)
        
    except Exception as e:
        return HTMLResponse(f"""
        <html>
            <head><title>OAuth Failed</title></head>
            <body>
                <h1>❌ OAuth Failed</h1>
                <p>Error: {str(e)}</p>
            </body>
        </html>
        """, status_code=500)


@router.post("/refresh")
async def refresh_token(account_id: str, session: Session = Depends(get_session)):
    """
    Manually refresh an account's access token.
    """
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if not account.token or not account.token.refresh_token:
        raise HTTPException(status_code=400, detail="Account has no refresh token")
    
    try:
        new_token = await refresh_access_token(account.token.refresh_token)
        
        account.token.access_token = new_token.access_token
        account.token.expires_in = new_token.expires_in
        account.token.expiry_timestamp = int(time.time()) + new_token.expires_in
        account.last_used = int(time.time())
        
        session.add(account)
        session.commit()
        
        return {
            "status": "success",
            "account_id": account_id,
            "expires_in": new_token.expires_in
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# OAuth Relay Endpoints (for production environments where redirect_uri cannot be changed)
# ============================================================================

# Fixed localhost callback for relay mode (must match Google Cloud Console config)
RELAY_CALLBACK_URI = "http://localhost:8000/api/oauth/callback"


class RelayCallbackRequest(BaseModel):
    """Request body for relay callback."""
    code: str
    state: str


@router.get("/start-relay")
async def start_oauth_relay(request: Request) -> OAuthStartResponse:
    """
    Start OAuth flow in relay mode.
    
    This is for production environments where the Google OAuth client's
    redirect_uri is configured for localhost only.
    
    The callback will go to localhost:8000, where a local relay application
    will forward the code back to this server.
    """
    # Always use localhost callback for relay mode
    redirect_uri = RELAY_CALLBACK_URI
    
    # Generate state for security
    state = secrets.token_urlsafe(32)
    _pending_states[state] = {
        "redirect_uri": redirect_uri,
        "created_at": time.time()
    }
    
    auth_url = generate_auth_url(redirect_uri, state)
    
    return OAuthStartResponse(auth_url=auth_url, state=state)


@router.post("/relay-callback")
async def relay_callback(
    data: RelayCallbackRequest,
    session: Session = Depends(get_session)
):
    """
    Receive OAuth callback forwarded from local relay application.
    
    The local relay receives Google's callback and forwards the code
    to this endpoint for token exchange and account creation.
    """
    code = data.code
    state = data.state
    
    # Verify state
    if state not in _pending_states:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    
    state_data = _pending_states.pop(state)
    redirect_uri = state_data["redirect_uri"]
    
    try:
        # Exchange code for tokens
        token_response = await exchange_code(code, redirect_uri)
        
        if not token_response.refresh_token:
            raise HTTPException(
                status_code=400,
                detail="Google did not return a refresh token. Please revoke app access at https://myaccount.google.com/permissions and try again."
            )
        
        # Get user info
        user_info = await get_user_info(token_response.access_token)
        
        # Fetch project_id (required for API calls)
        project_id = await fetch_project_id(token_response.access_token)
        
        # Save to database
        account_id = user_info.email.replace("@", "_at_").replace(".", "_")
        
        # Check if account exists
        existing = session.get(Account, account_id)
        if existing:
            # Update existing
            if existing.token:
                existing.token.access_token = token_response.access_token
                existing.token.refresh_token = token_response.refresh_token
                existing.token.expires_in = token_response.expires_in
                existing.token.expiry_timestamp = int(time.time()) + token_response.expires_in
                existing.token.project_id = project_id
            existing.name = user_info.get_display_name()
            existing.last_used = int(time.time())
            session.add(existing)
        else:
            # Create new
            token = Token(
                access_token=token_response.access_token,
                refresh_token=token_response.refresh_token,
                expires_in=token_response.expires_in,
                expiry_timestamp=int(time.time()) + token_response.expires_in,
                token_type="Bearer",
                email=user_info.email,
                project_id=project_id,
                account_id=account_id
            )
            account = Account(
                id=account_id,
                email=user_info.email,
                name=user_info.get_display_name(),
                created_at=int(time.time()),
                last_used=int(time.time())
            )
            account.token = token
            session.add(account)
        
        session.commit()
        
        # Auto-reload TokenManager to include the new account
        from app.core.token_manager import get_token_manager
        token_manager = get_token_manager()
        await token_manager.load_accounts()
        
        return {
            "status": "success",
            "email": user_info.email,
            "name": user_info.get_display_name(),
            "message": f"Account {user_info.email} has been added successfully."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

