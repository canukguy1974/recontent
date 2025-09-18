from packages.common.config import (
    GEMINI_IMAGE_MODEL_ID,
    GEMINI_TEXT_MODEL_ID,
    GOOGLE_CLOUD_PROJECT,
    GOOGLE_CLOUD_LOCATION,
)
import vertexai
from vertexai.preview.generative_models import GenerativeModel, Part

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
            generation_config={"candidate_count": 3, "response_modalities": ["TEXT", "IMAGE"]},
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
