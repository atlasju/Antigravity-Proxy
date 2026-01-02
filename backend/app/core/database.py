from sqlmodel import SQLModel, create_engine, Session, select
from app.models import account # Ensure models are imported for table creation
from app.models.user import User
from app.models.mapping import ModelMapping
from app.models.usage import UsageLog  # For usage statistics table

import os

sqlite_file_name = os.environ.get("AG_DB_PATH", "antigravity.db")
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    seed_default_user()

def seed_default_user():
    """Create the default admin user if not exists."""
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == "admin")).first()
        if not existing:
            default_user = User.create(username="admin", password="admin")
            session.add(default_user)
            session.commit()
            print(f"[Database] Created default user 'admin' with API key: {default_user.api_key}")
        else:
            print(f"[Database] Default user 'admin' already exists")

def get_session():
    with Session(engine) as session:
        yield session

