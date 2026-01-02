from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
import time

def current_timestamp() -> int:
    return int(time.time())

class TokenBase(SQLModel):
    access_token: str
    refresh_token: str
    expires_in: int
    expiry_timestamp: int
    token_type: str = "Bearer"
    email: Optional[str] = None
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    subscription_tier: Optional[str] = None  # FREE/PRO/ULTRA
    average_quota: Optional[float] = None    # Cached avg quota for routing

class Token(TokenBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: str = Field(foreign_key="account.id")
    
    account: "Account" = Relationship(back_populates="token")

class ModelQuotaBase(SQLModel):
    name: str
    percentage: int
    reset_time: str

class ModelQuota(ModelQuotaBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    quota_id: int = Field(foreign_key="quota.id")
    
    quota: "Quota" = Relationship(back_populates="models")

class QuotaBase(SQLModel):
    last_updated: int = Field(default_factory=current_timestamp)
    is_forbidden: bool = False
    subscription_tier: Optional[str] = None

class Quota(QuotaBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: str = Field(foreign_key="account.id")
    
    account: "Account" = Relationship(back_populates="quota")
    models: List[ModelQuota] = Relationship(back_populates="quota", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class AccountBase(SQLModel):
    id: str = Field(primary_key=True) # User provided or Google ID
    email: str
    name: Optional[str] = None
    created_at: int = Field(default_factory=current_timestamp)
    last_used: int = Field(default_factory=current_timestamp)

class Account(AccountBase, table=True):
    token: Optional[Token] = Relationship(back_populates="account", sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"})
    quota: Optional[Quota] = Relationship(back_populates="account", sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"})

class AccountCreate(AccountBase):
    token: TokenBase

class AccountRead(AccountBase):
    token: TokenBase
    quota: Optional[QuotaBase] = None
