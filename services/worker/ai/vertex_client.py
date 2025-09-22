from packages.common.config import (
    GEMINI_IMAGE_MODEL_ID,
    GEMINI_TEXT_MODEL_ID,
    GOOGLE_CLOUD_PROJECT,
    GOOGLE_CLOUD_LOCATION,
)
import vertexai
from vertexai.preview.generative_models import GenerativeModel, Part
from vertexai.preview.vision_models import ImageGenerationModel
import base64
from PIL import Image
from io import BytesIO

class VertexAIClient:
    def __init__(self):
        vertexai.init(project=GOOGLE_CLOUD_PROJECT, location=GOOGLE_CLOUD_LOCATION)
        self.image_model = GenerativeModel(GEMINI_IMAGE_MODEL_ID)
        self.text_model = GenerativeModel(GEMINI_TEXT_MODEL_ID)

    def composite(self, agent_bytes: bytes, room_bytes: bytes, brief: str) -> list[bytes]:
        system = (
            "You are a professional real-estate retoucher for Ontario listings. "
            "Make realistic, non-deceptive edits only."
        )
        instruction = (
            "Composite the person from the first image into the second (interior/exterior). "
            "Preserve identity/clothing; match perspective and lighting; add soft plausible shadow. "
            "Do not alter permanent fixtures, windows, or views. No text/logos. Return 3 options."
        )
        resp = self.image_model.generate_content(
            [
                system,
                f"Context: {brief}",
                Part.from_data(agent_bytes, mime_type="image/jpeg"),
                Part.from_data(room_bytes, mime_type="image/jpeg"),
                instruction,
            ],
            generation_config={"candidate_count": 3},
        )
        images = []
        for cand in getattr(resp, "candidates", []):
            for part in getattr(cand.content, "parts", []):
                if getattr(part, "inline_data", None):
                    images.append(part.inline_data.data)
        return images

    def caption(self, brief: str, staged: bool) -> str:
        disclosure = " One or more photos are virtually staged." if staged else ""
        resp = self.text_model.generate_content(
            f"Write a neutral real-estate caption (180–220 chars) with 3–5 neutral hashtags for: {brief}.{disclosure}"
        )
        return resp.text.strip()
    
    def inpaint(self, source_image_bytes: bytes, mask_image_bytes: bytes, prompt: str) -> bytes:
        """Apply AI-powered inpainting to edit specific regions of an image"""
        try:
            # Initialize Imagen model for inpainting
            model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
            
            # Convert bytes to PIL Images
            source_image = Image.open(BytesIO(source_image_bytes)).convert("RGB")
            mask_image = Image.open(BytesIO(mask_image_bytes)).convert("L")  # Grayscale for mask
            
            # Ensure images are same size
            if source_image.size != mask_image.size:
                mask_image = mask_image.resize(source_image.size, Image.Resampling.LANCZOS)
            
            # Convert PIL images back to bytes for Vertex AI
            source_buffer = BytesIO()
            source_image.save(source_buffer, format="JPEG", quality=95)
            source_bytes = source_buffer.getvalue()
            
            mask_buffer = BytesIO()
            mask_image.save(mask_buffer, format="PNG")
            mask_bytes = mask_buffer.getvalue()
            
            # Create enhanced inpainting prompt for real estate
            enhanced_prompt = f"""Professional real estate photography edit: {prompt}. 
            High quality, realistic, well-lit interior. Maintain architectural accuracy.
            Match existing lighting, perspective, and style. Professional MLS standards."""
            
            # Call Vertex AI Imagen for inpainting
            response = model.edit_image(
                base_image=Part.from_data(source_bytes, mime_type="image/jpeg"),
                mask=Part.from_data(mask_bytes, mime_type="image/png"),
                prompt=enhanced_prompt,
                number_of_images=1
            )
            
            # Extract the edited image
            if response.images:
                edited_image = response.images[0]
                return edited_image._image_bytes
            else:
                raise Exception("No edited image returned from Vertex AI")
                
        except Exception as e:
            print(f"Error in Vertex AI inpainting: {e}")
            # Fallback: return original image with overlay indicating edit attempt
            return self._create_fallback_edit(source_image_bytes, mask_image_bytes, prompt)
    
    def _create_fallback_edit(self, source_bytes: bytes, mask_bytes: bytes, prompt: str) -> bytes:
        """Create a fallback edit indication when AI inpainting fails"""
        try:
            from PIL import ImageDraw, ImageFont
            
            source_image = Image.open(BytesIO(source_bytes)).convert("RGB")
            draw = ImageDraw.Draw(source_image)
            
            # Add a subtle overlay indicating the edit was attempted
            overlay_text = f"AI Edit: {prompt[:30]}..."
            
            # Draw semi-transparent rectangle
            text_bbox = draw.textbbox((10, 10), overlay_text)
            draw.rectangle([text_bbox[0]-5, text_bbox[1]-5, text_bbox[2]+5, text_bbox[3]+5], 
                         fill=(0, 0, 0, 128))
            
            # Draw text
            draw.text((10, 10), overlay_text, fill="white")
            
            # Convert back to bytes
            buffer = BytesIO()
            source_image.save(buffer, format="JPEG", quality=95)
            return buffer.getvalue()
            
        except Exception as e:
            print(f"Error creating fallback edit: {e}")
            return source_bytes
