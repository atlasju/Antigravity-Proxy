from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.account import Account, AccountCreate, AccountRead, Token, Quota

router = APIRouter()

@router.get("/", response_model=list[AccountRead])
def list_accounts(session: Session = Depends(get_session)):
    accounts = session.exec(select(Account)).all()
    return accounts

@router.post("/", response_model=AccountRead)
def create_account(account: AccountCreate, session: Session = Depends(get_session)):
    # Create Token first
    token_data = account.token
    token_obj = Token.model_validate(token_data)
    
    # Create Account
    account_obj = Account.model_validate(account)
    account_obj.token = token_obj # Relationship
    
    session.add(account_obj)
    session.commit()
    session.refresh(account_obj)
    return account_obj

@router.delete("/{account_id}")
def delete_account(account_id: str, session: Session = Depends(get_session)):
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    session.delete(account)
    session.commit()
    
    # Auto-reload TokenManager
    from app.core.token_manager import get_token_manager
    import asyncio
    token_manager = get_token_manager()
    # Since this is a sync route but load_accounts is async, we wrap it
    # Ideally we should make this route async, but to keep minimal changes:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we are in an event loop (uvicorn), create a task
            loop.create_task(token_manager.load_accounts())
        else:
             loop.run_until_complete(token_manager.load_accounts())
    except RuntimeError:
        # Fallback if no loop
        asyncio.run(token_manager.load_accounts())

    return {"ok": True}
