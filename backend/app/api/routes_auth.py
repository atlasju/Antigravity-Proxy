"""
Authentication API Routes

Provides endpoints for:
- User login (returns JWT token)
- Current user info
- API key regeneration
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session

from app.core.database import engine
from app.core.auth import create_access_token, get_current_user
from app.models.user import User, UserLogin, UserResponse

router = APIRouter()


@router.post("/login")
async def login(credentials: UserLogin):
    """
    Authenticate user and return JWT token.
    """
    from app.core.auth import get_user_by_username
    
    user = get_user_by_username(credentials.username)
    if not user or not user.verify_password(credentials.password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    
    access_token = create_access_token(data={"sub": user.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(
            id=user.id,
            username=user.username,
            api_key=user.api_key,
            created_at=user.created_at
        )
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user info.
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        api_key=current_user.api_key,
        created_at=current_user.created_at
    )


@router.post("/regenerate-key")
async def regenerate_api_key(current_user: User = Depends(get_current_user)):
    """
    Regenerate the user's API key.
    """
    with Session(engine) as session:
        # Fetch fresh copy
        user = session.get(User, current_user.id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        new_key = user.regenerate_api_key()
        session.add(user)
        session.commit()
        
        return {
            "api_key": new_key,
            "message": "API key regenerated successfully"
        }


from pydantic import BaseModel

class PasswordChange(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(data: PasswordChange, current_user: User = Depends(get_current_user)):
    """
    Change user password.
    """
    from app.models.user import hash_password
    
    with Session(engine) as session:
        user = session.get(User, current_user.id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        if not user.verify_password(data.current_password):
            raise HTTPException(status_code=400, detail="Incorrect current password")
            
        user.hashed_password = hash_password(data.new_password)
        session.add(user)
        session.commit()
        
        return {"message": "Password updated successfully"}
