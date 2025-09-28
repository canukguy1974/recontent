from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from google.cloud.sql.connector import Connector, IPTypes
from fastapi import HTTPException, Depends, Header
from typing import Optional
from packages.common.config import DB_INSTANCE_CONN_NAME, DB_USER, DB_PASSWORD, DB_NAME
from db.models import User

connector = Connector()

def getconn():
    conn = connector.connect(
        DB_INSTANCE_CONN_NAME,
        "pg8000",
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        ip_type=IPTypes.PUBLIC,
    )
    return conn

engine = create_engine("postgresql+pg8000://", creator=getconn, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Simple authentication - for development/testing
# In production, you'd want to use proper JWT tokens, OAuth, etc.
def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user.
    For now, this is a simple implementation that looks for a user ID in the auth header.
    In production, this would validate JWT tokens, API keys, etc.
    """
    
    if not authorization:
        # For development - return first user if no auth provided
        user = db.query(User).first()
        if user:
            return user
        raise HTTPException(401, "Authentication required")
    
    # Simple format: "Bearer user_id" or "user_id"
    user_id_str = authorization.replace("Bearer ", "").strip()
    
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(401, "Invalid authentication format")
    
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(401, "Invalid user")
    
    if user.status != "active":
        raise HTTPException(401, "User account inactive")
    
    return user
