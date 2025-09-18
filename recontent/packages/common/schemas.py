from pydantic import BaseModel, Field

class CompositeJob(BaseModel):
    org_id: int
    user_id: int
    agent_gcs: str
    room_gcs: str
    brief: str = Field(default="")
