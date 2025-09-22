from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class ComposeRequest(BaseModel):
    prompt: str
    user_id: Optional[int] = None
    org_id: Optional[int] = None
    # Add more user info fields as needed

class ComposeResponse(BaseModel):
    image_url: str
    caption: str
    facts: List[str]
    cta: str

@router.post("/nlp/compose", response_model=ComposeResponse)
def compose_content(req: ComposeRequest):
    # TODO: Integrate real NLP/image generation logic
    # Placeholder response for now
    return ComposeResponse(
        image_url="https://placehold.co/600x400?text=Composed+Image",
        caption="Open house Sat and Sun 1-4 at 500 Some Street",
        facts=[
            "Spacious living room with natural light",
            "Recently renovated kitchen with modern appliances"
        ],
        cta="Contact us to schedule a tour!"
    )
