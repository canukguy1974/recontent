"""
Multi-Image Analysis Service for Combination Agent

This module handles analyzing multiple images together to extract relationships,
context, and generate intelligent combinations for social media posts.
"""
from typing import List, Dict, Any, Optional
import json
from dataclasses import dataclass, asdict
from io import BytesIO
from PIL import Image

from packages.common.gcs import download_bytes
from services.worker.ai.vertex_client import VertexAIClient
from services.worker.ai.mock_client import MockAIClient
from packages.common.config import MOCK_AI


@dataclass
class ImageAnalysis:
    """Analysis result for a single image"""
    asset_id: int
    gcs_uri: str
    image_type: str  # "property", "agent", "exterior", "interior", "staged", etc.
    room_type: Optional[str] = None  # "living_room", "kitchen", "bedroom", etc.
    style: Optional[str] = None  # "modern", "traditional", "contemporary", etc.
    lighting: Optional[str] = None  # "natural", "artificial", "mixed", etc.
    occupancy: Optional[str] = None  # "furnished", "empty", "staged", etc.
    features: List[str] = None  # ["fireplace", "hardwood", "granite", etc.]
    mood: Optional[str] = None  # "welcoming", "luxurious", "cozy", etc.
    quality_score: float = 0.0  # 0.0-1.0 rating of image quality
    confidence: float = 0.0  # 0.0-1.0 confidence in analysis

    def __post_init__(self):
        if self.features is None:
            self.features = []


@dataclass
class ImageSetAnalysis:
    """Analysis result for a set of images"""
    set_id: str
    images: List[ImageAnalysis]
    relationships: List[Dict[str, Any]]  # Connections between images
    property_story: str  # Narrative describing the property
    suggested_combinations: List[Dict[str, Any]]  # Recommended image groupings
    marketing_themes: List[str]  # Key selling points and themes
    target_audience: List[str]  # Suggested audience segments
    content_strategy: Dict[str, Any]  # Recommended posting strategy
    overall_confidence: float = 0.0


class MultiImageAnalyzer:
    """Service for analyzing multiple images together using AI"""
    
    def __init__(self):
        self._ai_client = MockAIClient() if MOCK_AI else VertexAIClient()
    
    async def analyze_image_set(self, asset_ids: List[int], gcs_uris: List[str], 
                               context: Optional[Dict[str, Any]] = None) -> ImageSetAnalysis:
        """
        Analyze a set of images to understand their relationships and generate insights
        
        Args:
            asset_ids: List of asset IDs from the database
            gcs_uris: List of GCS URIs for the images
            context: Optional context information (property details, agent info, etc.)
        
        Returns:
            ImageSetAnalysis with comprehensive insights
        """
        if len(asset_ids) != len(gcs_uris):
            raise ValueError("Asset IDs and GCS URIs lists must be the same length")
        
        if len(gcs_uris) < 2:
            raise ValueError("Multi-image analysis requires at least 2 images")
        
        # Generate unique set ID
        set_id = f"set_{hash(tuple(sorted(gcs_uris)))}"
        
        # Analyze individual images first
        individual_analyses = []
        image_bytes_list = []
        
        for asset_id, gcs_uri in zip(asset_ids, gcs_uris):
            # Download image bytes for AI analysis
            image_bytes = download_bytes(gcs_uri)
            image_bytes_list.append(image_bytes)
            
            # Analyze individual image
            analysis = await self._analyze_single_image(asset_id, gcs_uri, image_bytes, context)
            individual_analyses.append(analysis)
        
        # Perform collective analysis using AI
        if MOCK_AI:
            collective_analysis = self._mock_collective_analysis(individual_analyses)
        else:
            collective_analysis = await self._ai_collective_analysis(
                individual_analyses, image_bytes_list, context
            )
        
        return ImageSetAnalysis(
            set_id=set_id,
            images=individual_analyses,
            **collective_analysis
        )
    
    async def _analyze_single_image(self, asset_id: int, gcs_uri: str, 
                                   image_bytes: bytes, context: Optional[Dict[str, Any]] = None) -> ImageAnalysis:
        """Analyze a single image to extract its characteristics"""
        
        if MOCK_AI:
            return self._mock_single_analysis(asset_id, gcs_uri)
        
        # Use AI to analyze the image
        try:
            # Prepare image for AI analysis
            image = Image.open(BytesIO(image_bytes))
            
            # Build analysis prompt
            prompt = """
            Analyze this real estate image and provide a JSON response with the following structure:
            {
                "image_type": "property|agent|exterior|interior|staged",
                "room_type": "living_room|kitchen|bedroom|bathroom|dining_room|office|other|null",
                "style": "modern|traditional|contemporary|rustic|luxury|other|null",
                "lighting": "natural|artificial|mixed|poor|excellent|null",
                "occupancy": "furnished|empty|staged|partial|null",
                "features": ["feature1", "feature2", "..."],
                "mood": "welcoming|luxurious|cozy|spacious|bright|warm|professional|other|null",
                "quality_score": 0.85,
                "confidence": 0.90
            }
            
            Focus on real estate marketing attributes. Be specific and accurate.
            """
            
            if hasattr(self._ai_client, 'analyze_image'):
                analysis_result = await self._ai_client.analyze_image(image_bytes, prompt)
            else:
                # Fallback to mock analysis if AI client doesn't support image analysis
                return self._mock_single_analysis(asset_id, gcs_uri)
            
            # Parse AI response
            try:
                analysis_data = json.loads(analysis_result)
                return ImageAnalysis(
                    asset_id=asset_id,
                    gcs_uri=gcs_uri,
                    **analysis_data
                )
            except json.JSONDecodeError:
                # Fallback to mock if JSON parsing fails
                return self._mock_single_analysis(asset_id, gcs_uri)
                
        except Exception as e:
            print(f"Image analysis failed for {gcs_uri}: {e}")
            return self._mock_single_analysis(asset_id, gcs_uri)
    
    def _mock_single_analysis(self, asset_id: int, gcs_uri: str) -> ImageAnalysis:
        """Mock analysis for development/testing"""
        # Infer basic info from URI/asset patterns
        uri_lower = gcs_uri.lower()
        
        if "agent" in uri_lower or "headshot" in uri_lower:
            return ImageAnalysis(
                asset_id=asset_id,
                gcs_uri=gcs_uri,
                image_type="agent",
                mood="professional",
                features=["professional_appearance"],
                quality_score=0.85,
                confidence=0.90
            )
        elif "exterior" in uri_lower or "outside" in uri_lower:
            return ImageAnalysis(
                asset_id=asset_id,
                gcs_uri=gcs_uri,
                image_type="exterior",
                style="contemporary",
                lighting="natural",
                features=["landscaping", "entrance"],
                mood="welcoming",
                quality_score=0.80,
                confidence=0.85
            )
        else:
            return ImageAnalysis(
                asset_id=asset_id,
                gcs_uri=gcs_uri,
                image_type="interior",
                room_type="living_room",
                style="modern",
                lighting="natural",
                occupancy="furnished",
                features=["hardwood_floors", "large_windows"],
                mood="spacious",
                quality_score=0.88,
                confidence=0.92
            )
    
    async def _ai_collective_analysis(self, individual_analyses: List[ImageAnalysis], 
                                     image_bytes_list: List[bytes], 
                                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Use AI to analyze the set of images collectively"""
        
        # Build collective analysis prompt
        individual_summaries = []
        for analysis in individual_analyses:
            individual_summaries.append({
                "type": analysis.image_type,
                "room": analysis.room_type,
                "style": analysis.style,
                "features": analysis.features,
                "mood": analysis.mood
            })
        
        prompt = f"""
        Analyze this set of real estate images collectively and provide insights:
        
        Individual image analyses: {json.dumps(individual_summaries, indent=2)}
        
        Context: {json.dumps(context or {}, indent=2)}
        
        Provide a JSON response with:
        {{
            "relationships": [
                {{"type": "style_consistency", "images": [0, 1], "strength": 0.9, "description": "..."}}
            ],
            "property_story": "A compelling narrative about this property based on the images",
            "suggested_combinations": [
                {{"images": [0, 1, 2], "purpose": "virtual_tour", "description": "..."}}
            ],
            "marketing_themes": ["luxury", "spacious", "modern"],
            "target_audience": ["young_professionals", "families"],
            "content_strategy": {{
                "primary_message": "...",
                "posting_schedule": "...",
                "platform_focus": ["instagram", "facebook"]
            }},
            "overall_confidence": 0.85
        }}
        """
        
        try:
            if hasattr(self._ai_client, 'analyze_image_set'):
                result = await self._ai_client.analyze_image_set(image_bytes_list, prompt)
            else:
                # Use text-based analysis if image set analysis not available
                result = await self._ai_client.generate_text_response(prompt)
            
            return json.loads(result)
        except Exception as e:
            print(f"Collective AI analysis failed: {e}")
            return self._mock_collective_analysis(individual_analyses)
    
    def _mock_collective_analysis(self, individual_analyses: List[ImageAnalysis]) -> Dict[str, Any]:
        """Mock collective analysis for development/testing"""
        
        # Analyze image types in the set
        image_types = [analysis.image_type for analysis in individual_analyses]
        has_agent = "agent" in image_types
        has_property = any(t in ["interior", "exterior", "property"] for t in image_types)
        
        # Generate mock relationships
        relationships = []
        if has_agent and has_property:
            relationships.append({
                "type": "agent_property_match",
                "images": [0, 1],
                "strength": 0.9,
                "description": "Agent and property images suitable for combined marketing"
            })
        
        # Build property story
        if has_agent and has_property:
            story = "Professional agent showcasing a beautiful property with modern amenities and excellent presentation"
        elif has_property:
            story = "Stunning property featuring modern design and high-quality finishes throughout"
        else:
            story = "Professional real estate marketing materials showcasing quality and expertise"
        
        # Suggest combinations based on available images
        combinations = []
        if len(individual_analyses) >= 3:
            combinations.append({
                "images": [0, 1, 2],
                "purpose": "property_showcase",
                "description": "Complete property presentation with multiple angles"
            })
        if has_agent:
            combinations.append({
                "images": [i for i, a in enumerate(individual_analyses) if a.image_type != "agent"][:2] + 
                         [i for i, a in enumerate(individual_analyses) if a.image_type == "agent"][:1],
                "purpose": "agent_listing",
                "description": "Agent-focused marketing with property highlights"
            })
        
        return {
            "relationships": relationships,
            "property_story": story,
            "suggested_combinations": combinations,
            "marketing_themes": ["professional", "quality", "modern"],
            "target_audience": ["homebuyers", "investors"],
            "content_strategy": {
                "primary_message": "Professional real estate marketing",
                "posting_schedule": "peak_hours",
                "platform_focus": ["facebook", "instagram"]
            },
            "overall_confidence": 0.80
        }
    
    def serialize_analysis(self, analysis: ImageSetAnalysis) -> Dict[str, Any]:
        """Convert analysis to JSON-serializable format"""
        return {
            "set_id": analysis.set_id,
            "images": [asdict(img) for img in analysis.images],
            "relationships": analysis.relationships,
            "property_story": analysis.property_story,
            "suggested_combinations": analysis.suggested_combinations,
            "marketing_themes": analysis.marketing_themes,
            "target_audience": analysis.target_audience,
            "content_strategy": analysis.content_strategy,
            "overall_confidence": analysis.overall_confidence
        }