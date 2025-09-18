from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from google.cloud.sql.connector import Connector, IPTypes
from packages.common.config import DB_INSTANCE_CONN_NAME, DB_USER, DB_PASSWORD, DB_NAME

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
