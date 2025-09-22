from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import base64
from io import BytesIO
from uuid import uuid4

# Import our AI clients
from services.worker.ai.mock_client import MockAIClient
from services.worker.ai.vertex_client import VertexAIClient
from packages.common.config import MOCK_AI, BUCKET_PROCESSED, GOOGLE_CLOUD_PROJECT
from packages.common.gcs import upload_bytes, get_signed_url, download_bytes

router = APIRouter()

# Initialize AI client based on config
_ai = MockAIClient() if MOCK_AI else VertexAIClient()

class ComposeRequest(BaseModel):
    prompt: str
    user_id: Optional[int] = None
    org_id: Optional[int] = None
    # For agent insertion
    agent_image_gcs: Optional[str] = None  # GCS URI like "gs://bucket/agent.jpg"
    room_image_gcs: Optional[str] = None   # GCS URI like "gs://bucket/room.jpg"
    composition_type: Optional[str] = "text_to_image"  # "text_to_image", "agent_insertion", "virtual_staging", "smart_edit"
    # For smart editing with brush masks
    mask_data: Optional[str] = None  # Base64 encoded mask image where white = edit area
    edit_instruction: Optional[str] = None  # What to do with the masked area

class ComposeResponse(BaseModel):
    image_url: str
    caption: str
    facts: List[str]
    cta: str

@router.post("/compose", response_model=ComposeResponse)
async def compose_content(req: ComposeRequest):
    """Generate AI-powered real estate content from natural language prompts"""
    try:
        # Determine composition type and generate appropriate image
        if req.composition_type == "agent_insertion" and req.agent_image_gcs and req.room_image_gcs:
            image_url = await generate_agent_insertion(req.agent_image_gcs, req.room_image_gcs, req.prompt, req.org_id or 1)
            staged = False  # Agent insertion is not virtual staging
        elif req.composition_type == "virtual_staging":
            # Virtual staging: transform empty rooms into furnished spaces
            if req.room_image_gcs:
                image_url = await generate_virtual_staging(req.room_image_gcs, req.prompt, req.org_id or 1)
            else:
                image_url = await generate_image_from_prompt(req.prompt, req.org_id or 1)
            staged = True
        elif req.composition_type == "smart_edit":
            # Smart editing: use brush masks + NLP for precise editing
            if req.room_image_gcs and req.mask_data:
                image_url = await generate_smart_edit(req.room_image_gcs, req.mask_data, req.edit_instruction or req.prompt, req.org_id or 1)
            else:
                image_url = await generate_image_from_prompt(req.prompt, req.org_id or 1)
            staged = "remove" not in req.prompt.lower()  # If removing, not staging
        else:
            # Default to text-to-image generation
            image_url = await generate_image_from_prompt(req.prompt, req.org_id or 1)
            staged = "staging" in req.prompt.lower() or "furnished" in req.prompt.lower()
        
        # Generate marketing content using the same AI
        caption = _ai.caption(req.prompt, staged=staged)
        
        # Generate engaging facts based on the prompt
        facts = generate_facts_from_prompt(req.prompt)
        
        # Generate appropriate CTA
        cta = generate_cta_from_prompt(req.prompt)
        
        return ComposeResponse(
            image_url=image_url,
            caption=caption,
            facts=facts,
            cta=cta
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate content: {str(e)}")

async def generate_image_from_prompt(prompt: str, org_id: int) -> str:
    """Generate an image from a natural language prompt using Vertex AI"""
    if MOCK_AI:
        # Return placeholder for mock mode
        return "https://placehold.co/600x400?text=AI+Generated+Image"
    
    try:
        # Create enhanced real estate prompt for image generation
        real_estate_prompt = f"""Professional real estate photography: {prompt}. 
        High quality, well-lit, bright and inviting interior/exterior photograph. 
        Professional photography style, 4K resolution, perfect lighting, 
        suitable for luxury real estate marketing materials."""
        
        # Use Vertex AI's text model to generate image
        # Note: This is a simplified approach - in production you'd use Imagen
        response = _ai.text_model.generate_content([
            "Generate a detailed, professional description for a real estate photograph",
            f"Based on this request: {real_estate_prompt}",
            "Respond with only a detailed visual description suitable for image generation"
        ])
        
        description = response.text.strip()
        
        # For now, we'll create a unique placeholder that shows we're using Vertex AI
        # In a real implementation, this would call Imagen API
        unique_id = str(uuid4())[:8]
        image_url = f"https://placehold.co/800x600/4A90E2/FFFFFF?text=Vertex+AI+Generated+{unique_id}"
        
        # TODO: Replace with actual Imagen API call:
        # from vertexai.preview.vision_models import ImageGenerationModel
        # model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
        # images = model.generate_images(prompt=real_estate_prompt, number_of_images=1)
        # Upload generated image to GCS and return public URL
        
        return image_url
        
    except Exception as e:
        print(f"Error generating image with Vertex AI: {e}")
        # Fallback to enhanced placeholder
        return f"https://placehold.co/600x400/E74C3C/FFFFFF?text=AI+Error+{str(e)[:20]}"

async def generate_agent_insertion(agent_gcs: str, room_gcs: str, prompt: str, org_id: int) -> str:
    """Composite a real estate agent into a property photo using Vertex AI"""
    try:
        # For now, create a demonstration placeholder that shows agent insertion is working
        # In production, this would use Vertex AI Imagen for real composition
        
        unique_id = str(uuid4())[:8]
        
        # Create a descriptive placeholder that shows the concept
        demo_url = f"https://placehold.co/800x600/2ECC71/FFFFFF?text=Agent+Insertion+{unique_id}+%0AAgent:%20{agent_gcs.split('/')[-1][:8]}+%0ARoom:%20{room_gcs.split('/')[-1][:8]}"
        
        # TODO: Implement real Vertex AI Imagen composition
        # agent_bytes = download_bytes(agent_gcs)  
        # room_bytes = download_bytes(room_gcs)
        # composite_images = _ai.composite(agent_bytes, room_bytes, enhanced_prompt)
        # Upload result to GCS and return signed URL
        
        return demo_url
            
    except Exception as e:
        print(f"Error in agent insertion: {e}")
        return f"https://placehold.co/600x400/E74C3C/FFFFFF?text=Insertion+Error+{str(e)[:10]}"

async def generate_virtual_staging(room_gcs: str, prompt: str, org_id: int) -> str:
    """Transform empty rooms into beautifully staged spaces using AI"""
    try:
        unique_id = str(uuid4())[:8]
        
        # Parse staging style from prompt
        staging_style = "modern"  # default
        if "scandinavian" in prompt.lower():
            staging_style = "scandinavian"
        elif "traditional" in prompt.lower():
            staging_style = "traditional"
        elif "contemporary" in prompt.lower():
            staging_style = "contemporary"
        elif "minimalist" in prompt.lower():
            staging_style = "minimalist"
        
        # Extract room type from prompt or GCS path
        room_type = "living room"  # default
        if "kitchen" in prompt.lower():
            room_type = "kitchen"
        elif "bedroom" in prompt.lower():
            room_type = "bedroom"
        elif "dining" in prompt.lower():
            room_type = "dining room"
        elif "office" in prompt.lower():
            room_type = "office"
        
        # Create demonstration URL showing staging details
        demo_url = f"https://placehold.co/800x600/3498DB/FFFFFF?text=Virtual+Staging+{unique_id}+%0AStyle:%20{staging_style.title()}+%0ARoom:%20{room_type.title()}+%0ASource:%20{room_gcs.split('/')[-1][:12]}"
        
        # TODO: Implement real Imagen inpainting for virtual staging
        # This would involve:
        # 1. Download empty room image from GCS
        # 2. Use Vertex AI Imagen for inpainting/furniture placement
        # 3. Apply staging style prompts based on instructions.md
        # 4. Upload staged result to GCS and return signed URL
        
        # Placeholder implementation:
        # room_bytes = download_bytes(room_gcs)
        # staging_prompt = f"Transform this {room_type} with {staging_style} furniture and decor. {prompt}"
        # staged_images = await stage_room_with_ai(room_bytes, staging_prompt)
        # return upload_and_get_signed_url(staged_images[0], org_id)
        
        return demo_url
        
    except Exception as e:
        print(f"Error in virtual staging: {e}")
        return f"https://placehold.co/600x400/E67E22/FFFFFF?text=Staging+Error+{str(e)[:10]}"

async def generate_smart_edit(image_gcs: str, mask_data: str, edit_instruction: str, org_id: int) -> str:
    """Apply intelligent editing to specific areas using brush masks and NLP instructions"""
    try:
        import base64
        
        unique_id = str(uuid4())[:8]
        
        # Parse the edit instruction to understand the operation
        operation = "modify"  # default
        if any(word in edit_instruction.lower() for word in ["remove", "delete", "erase"]):
            operation = "remove"
        elif any(word in edit_instruction.lower() for word in ["replace", "change", "swap"]):
            operation = "replace"
        elif any(word in edit_instruction.lower() for word in ["brighten", "darken", "lighting"]):
            operation = "lighting"
        elif any(word in edit_instruction.lower() for word in ["color", "paint", "recolor"]):
            operation = "recolor"
        
        # Detect what object/area is being edited (this would use computer vision in production)
        likely_object = "object"
        if "furniture" in edit_instruction.lower():
            likely_object = "furniture"
        elif "wall" in edit_instruction.lower():
            likely_object = "wall"
        elif "couch" in edit_instruction.lower() or "sofa" in edit_instruction.lower():
            likely_object = "couch"
        elif "lighting" in edit_instruction.lower() or "light" in edit_instruction.lower():
            likely_object = "lighting"
        elif "counter" in edit_instruction.lower():
            likely_object = "counter"
        
        if MOCK_AI:
            # Create demonstration URL showing the smart edit details for mock mode
            demo_url = f"https://placehold.co/800x600/9B59B6/FFFFFF?text=Smart+Edit+{unique_id}+%0AOperation:%20{operation.title()}+%0ATarget:%20{likely_object.title()}+%0ASource:%20{image_gcs.split('/')[-1][:12]}"
            return demo_url
        
        # Real AI-powered inpainting implementation
        try:
            # Step 1: Decode base64 mask data
            mask_bytes = base64.b64decode(mask_data)
            
            # Step 2: Download source image from GCS or handle URL
            if image_gcs.startswith("gs://"):
                source_bytes = download_bytes(image_gcs)
            else:
                # Handle external URLs (like Unsplash) using urllib
                import urllib.request
                with urllib.request.urlopen(image_gcs) as response:
                    source_bytes = response.read()
            
            # Step 3: Use Vertex AI Imagen for inpainting
            edited_image_bytes = _ai.inpaint(source_bytes, mask_bytes, edit_instruction)
            
            # Step 4: Upload result to GCS
            result_filename = f"smart_edit_{unique_id}_{operation}_{org_id}.jpg"
            result_gcs_uri = f"gs://{BUCKET_PROCESSED}/org_{org_id}/{result_filename}"
            
            upload_bytes(result_gcs_uri, edited_image_bytes, "image/jpeg")
            
            # Step 5: Return signed URL for the edited image  
            from packages.common.gcs import get_signed_url
            signed_url = get_signed_url(result_gcs_uri, expiration_minutes=60)
            
            return signed_url
            
        except Exception as e:
            print(f"Error in real AI inpainting: {e}")
            # Fallback to demonstration URL on error
            demo_url = f"https://placehold.co/800x600/E74C3C/FFFFFF?text=Inpaint+Error+{unique_id}+%0A{str(e)[:30]}"
            return demo_url
        
    except Exception as e:
        print(f"Error in smart editing: {e}")
        return f"https://placehold.co/600x400/E74C3C/FFFFFF?text=Edit+Error+{str(e)[:10]}"

def generate_facts_from_prompt(prompt: str) -> List[str]:
    """Extract or generate relevant facts from the prompt"""
    facts = []
    
    # Look for room types and add specific facts
    if "living room" in prompt.lower():
        facts.append("Spacious living room with natural light")
    if "kitchen" in prompt.lower():
        facts.append("Modern kitchen with updated appliances")  
    if "bedroom" in prompt.lower():
        facts.append("Comfortable bedrooms with ample storage")
    if "bathroom" in prompt.lower():
        facts.append("Updated bathrooms with modern fixtures")
    if "dining" in prompt.lower():
        facts.append("Elegant dining area perfect for entertaining")
    if "office" in prompt.lower():
        facts.append("Dedicated workspace with excellent natural light")
    
    # Add staging-specific facts
    if "staging" in prompt.lower() or "furnished" in prompt.lower() or "virtual" in prompt.lower():
        facts.append("Professionally staged for maximum appeal")
        
        # Add style-specific facts
        if "scandinavian" in prompt.lower():
            facts.append("Clean lines and minimalist Nordic design aesthetic")
        elif "contemporary" in prompt.lower():
            facts.append("Contemporary furnishings with modern appeal")
        elif "traditional" in prompt.lower():
            facts.append("Classic traditional styling with timeless elegance")
        elif "minimalist" in prompt.lower():
            facts.append("Minimalist design emphasizing space and light")
    
    # Add architecture and staging benefits
    if any(word in prompt.lower() for word in ["staging", "furnished", "virtual"]):
        facts.append("Helps buyers visualize the full potential of the space")
    
    # Add smart editing benefits
    if any(word in prompt.lower() for word in ["remove", "edit", "enhance", "improve"]):
        facts.append("Professionally enhanced to highlight property features")
        
        # Add specific editing benefits
        if "lighting" in prompt.lower():
            facts.append("Optimized lighting showcases the space beautifully")
        if "remove" in prompt.lower():
            facts.append("Clutter-free presentation focuses on key features")
        if "color" in prompt.lower():
            facts.append("Updated color scheme appeals to modern buyers")
    
    # Default facts if none found
    if not facts:
        facts = [
            "Prime location with excellent amenities",
            "Move-in ready condition"
        ]
    
    return facts

def generate_cta_from_prompt(prompt: str) -> str:
    """Generate appropriate call-to-action based on prompt context"""
    if "open house" in prompt.lower():
        return "Join us at the open house this weekend!"
    elif "showing" in prompt.lower():
        return "Schedule your private showing today!"
    elif "tour" in prompt.lower():
        return "Book your virtual or in-person tour now!"
    else:
        return "Contact us for more information and to schedule a viewing!"
