from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum,
    Boolean,
    ForeignKey,
    JSON,
    BigInteger,
)
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()

class Plan(enum.Enum):
    BASIC = "basic"
    PRO = "pro"
    PREMIUM = "premium"

class AssetKind(enum.Enum):
    HEADSHOT = "headshot"
    LISTING = "listing"
    MASK = "mask"
    OUTPUT = "output"

class JobType(enum.Enum):
    COMPOSITE = "composite"
    STAGING = "staging"
    CAPTION = "caption"
    PUBLISH = "publish"

class JobStatus(enum.Enum):
    CREATED = "created"
    QUEUED = "queued"
    RENDERING = "rendering"
    FAILED = "failed"
    COMPLETE = "complete"

class Org(Base):
    __tablename__ = "orgs"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    plan = Column(Enum(Plan), nullable=False)
    weekly_limit = Column(Integer, nullable=False, default=2)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("orgs.id"), nullable=False)
    email = Column(String, unique=True, nullable=False)
    role = Column(String, default="creator")
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    org = relationship("Org")

class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("orgs.id"), nullable=False)
    owner_user_id = Column(Integer, ForeignKey("users.id"))
    kind = Column(Enum(AssetKind), nullable=False)
    gcs_uri = Column(String, nullable=False)
    width = Column(Integer)
    height = Column(Integer)
    checksum = Column(String)
    staged = Column(Boolean, default=False)
    contains_people = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(BigInteger, primary_key=True)
    org_id = Column(Integer, ForeignKey("orgs.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(Enum(JobType), nullable=False)
    input_asset_ids = Column(JSON, default=list)
    status = Column(Enum(JobStatus), default=JobStatus.CREATED)
    model = Column(String)
    params = Column(JSON, default=dict)
    output_asset_ids = Column(JSON, default=list)
    error = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("orgs.id"), nullable=False)
    platform = Column(String, nullable=False)
    caption = Column(String)
    image_asset_ids = Column(JSON, default=list)
    scheduled_for = Column(DateTime)
    published_at = Column(DateTime)
    external_id = Column(String)
    status = Column(String, default="draft")

class Quota(Base):
    __tablename__ = "quotas"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("orgs.id"), nullable=False)
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    weekly_limit = Column(Integer, nullable=False, default=2)
    used_count = Column(Integer, default=0)
