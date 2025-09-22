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
    
    def analyze_editing_instruction(self, prompt: str, image_context: str = None) -> dict:
        """Analyze natural language editing instructions using AI to detect complex operations"""
        try:
            analysis_prompt = f"""
            Analyze this image editing instruction and return a structured analysis in JSON format:
            
            Instruction: "{prompt}"
            {f"Image context: {image_context}" if image_context else ""}
            
            Identify:
            1. Primary operation type: remove, replace, modify, enhance, color_change, lighting_adjust, texture_change, style_transfer
            2. Target elements: what specific objects/areas to edit (e.g., "furniture", "walls", "couch", "lighting")
            3. Operation parameters: specific details like colors, materials, styles
            4. Confidence score: 0.0-1.0 for how clear the instruction is
            5. Fallback operation: simpler operation if primary fails
            
            Return ONLY valid JSON in this exact format:
            {{
                "primary_operation": "operation_type",
                "target_elements": ["element1", "element2"],
                "parameters": {{
                    "color": "color_name_if_applicable",
                    "material": "material_if_applicable", 
                    "style": "style_if_applicable",
                    "intensity": "low/medium/high_if_applicable"
                }},
                "confidence": 0.85,
                "fallback_operation": "simpler_operation",
                "reasoning": "brief explanation of analysis"
            }}
            """
            
            response = self.text_model.generate_content(analysis_prompt)
            
            # Parse the JSON response
            import json
            result = json.loads(response.text.strip())
            
            # Validate required fields
            if not all(key in result for key in ["primary_operation", "target_elements", "confidence"]):
                raise ValueError("Invalid analysis format returned")
                
            return result
            
        except Exception as e:
            print(f"Error in AI instruction analysis: {e}")
            # Fallback to basic keyword matching
            return self._fallback_operation_detection(prompt)
    
    def generate_enhanced_content(self, prompt: str, composition_type: str, operation_analysis: dict = None, 
                                 agent_info: dict = None, property_context: dict = None) -> dict:
        """Generate personalized marketing content using AI analysis"""
        try:
            # Build context for AI content generation
            context_parts = [
                f"Property visualization: {prompt}",
                f"Composition type: {composition_type}"
            ]
            
            if operation_analysis:
                context_parts.append(f"Image modifications: {operation_analysis.get('reasoning', 'Standard processing')}")
                
            if property_context:
                if property_context.get('room_type'):
                    context_parts.append(f"Room type: {property_context['room_type']}")
                if property_context.get('style'):
                    context_parts.append(f"Style: {property_context['style']}")
                if property_context.get('staging_status'):
                    context_parts.append(f"Staging: {property_context['staging_status']}")
                    
            if agent_info:
                if agent_info.get('name'):
                    context_parts.append(f"Agent: {agent_info['name']}")
                if agent_info.get('specialization'):
                    context_parts.append(f"Specialization: {agent_info['specialization']}")
            
            context_summary = ". ".join(context_parts)
            
            # Generate AI-powered content
            content_prompt = f"""
            As a professional real estate marketing expert, create engaging social media content for this property visualization:
            
            Context: {context_summary}
            
            Generate content in this JSON format:
            {{
                "caption": "Engaging 180-220 character caption with 3-5 relevant hashtags",
                "facts": ["Fact 1 about the property/space", "Fact 2 highlighting key features", "Fact 3 about benefits/appeal"],
                "cta": "Compelling call-to-action that encourages engagement"
            }}
            
            Requirements:
            - Caption: Professional yet engaging, focus on lifestyle benefits and visual appeal
            - Facts: Specific, compelling, and relevant to the space/modifications shown
            - CTA: Action-oriented and contextually appropriate 
            - Include virtual staging disclosure if staging was mentioned
            - Use real estate best practices for social media engagement
            
            Return ONLY valid JSON.
            """
            
            response = self.text_model.generate_content(content_prompt)
            
            # Debug: Log the raw response
            raw_response = response.text.strip()
            print(f"Raw AI response: {raw_response[:200]}...")
            
            # Clean the response - remove markdown code fences if present
            cleaned_response = raw_response
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]   # Remove ```
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]  # Remove trailing ```
            
            cleaned_response = cleaned_response.strip()
            print(f"Cleaned response: {cleaned_response[:200]}...")
            
            # Parse the JSON response
            import json
            result = json.loads(cleaned_response)
            
            # Validate required fields
            if not all(key in result for key in ["caption", "facts", "cta"]):
                raise ValueError("Invalid content format returned")
                
            return result
            
        except Exception as e:
            print(f"Error in AI content generation: {e}")
            # Fallback to basic content generation
            return self._fallback_content_generation(prompt, composition_type)
    
    def _fallback_content_generation(self, prompt: str, composition_type: str) -> dict:
        """Fallback content generation using the existing caption method"""
        staged = composition_type in ["virtual_staging", "smart_edit"] or "staging" in prompt.lower()
        
        return {
            "caption": self.caption(prompt, staged=staged),
            "facts": [
                "Prime location with excellent amenities",
                "Move-in ready condition",
                "Professional photography highlights key features"
            ],
            "cta": "Contact us for more information and to schedule a viewing!"
        }
    
    def _fallback_operation_detection(self, prompt: str) -> dict:
        """Fallback to basic keyword matching if AI analysis fails"""
        operation = "modify"
        target_elements = ["object"]
        confidence = 0.6
        
        # Basic keyword matching (original logic)
        if any(word in prompt.lower() for word in ["remove", "delete", "erase"]):
            operation = "remove"
            confidence = 0.8
        elif any(word in prompt.lower() for word in ["replace", "change", "swap"]):
            operation = "replace"
            confidence = 0.7
        elif any(word in prompt.lower() for word in ["brighten", "darken", "lighting"]):
            operation = "lighting_adjust"
            confidence = 0.7
        elif any(word in prompt.lower() for word in ["color", "paint", "recolor"]):
            operation = "color_change"
            confidence = 0.7
        
        # Basic target detection
        if "furniture" in prompt.lower():
            target_elements = ["furniture"]
        elif "wall" in prompt.lower():
            target_elements = ["wall"]
        elif any(word in prompt.lower() for word in ["couch", "sofa"]):
            target_elements = ["couch"]
        elif any(word in prompt.lower() for word in ["lighting", "light"]):
            target_elements = ["lighting"]
        
        return {
            "primary_operation": operation,
            "target_elements": target_elements,
            "parameters": {},
            "confidence": confidence,
            "fallback_operation": "modify",
            "reasoning": "Fallback keyword matching used"
        }
    
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
