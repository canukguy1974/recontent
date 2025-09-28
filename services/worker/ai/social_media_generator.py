"""
Social Media Post Generation Engine

Generates platform-specific social media posts with proper formatting,
dimensions, and content optimization for different platforms.
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import re
from datetime import datetime

from services.worker.ai.vertex_client import VertexAIClient
from packages.common.logging import get_logger

log = get_logger("social-media-generator")

class SocialPlatform(Enum):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook" 
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    PINTEREST = "pinterest"
    TIKTOK = "tiktok"

@dataclass
class PlatformSpecs:
    name: str
    image_dimensions: Dict[str, tuple]  # format: (width, height)
    text_limits: Dict[str, int]
    hashtag_limit: int
    supports_carousel: bool
    supports_video: bool
    aspect_ratios: List[str]

@dataclass
class PostContent:
    platform: SocialPlatform
    caption: str
    hashtags: List[str]
    image_config: Dict[str, Any]
    engagement_hooks: List[str]
    call_to_action: Optional[str] = None
    scheduling_suggestions: List[str] = None

@dataclass
class SocialMediaPost:
    post_id: str
    platform: SocialPlatform
    content: PostContent
    asset_ids: List[int]
    performance_score: float
    estimated_reach: Optional[int] = None
    best_posting_times: List[str] = None

class SocialMediaGenerator:
    """Generates optimized social media posts for different platforms"""
    
    def __init__(self, vertex_client: VertexAIClient):
        self.vertex_client = vertex_client
        self.platform_specs = self._init_platform_specs()
    
    def _init_platform_specs(self) -> Dict[SocialPlatform, PlatformSpecs]:
        """Initialize platform-specific configurations"""
        return {
            SocialPlatform.INSTAGRAM: PlatformSpecs(
                name="Instagram",
                image_dimensions={
                    "square": (1080, 1080),
                    "portrait": (1080, 1350),
                    "landscape": (1080, 566),
                    "story": (1080, 1920),
                    "reel": (1080, 1920)
                },
                text_limits={
                    "caption": 2200,
                    "story_text": 150
                },
                hashtag_limit=30,
                supports_carousel=True,
                supports_video=True,
                aspect_ratios=["1:1", "4:5", "1.91:1", "9:16"]
            ),
            SocialPlatform.FACEBOOK: PlatformSpecs(
                name="Facebook",
                image_dimensions={
                    "post": (1200, 630),
                    "story": (1080, 1920),
                    "cover": (1200, 315),
                    "event": (1920, 1080)
                },
                text_limits={
                    "post": 63206,
                    "story_text": 200
                },
                hashtag_limit=20,
                supports_carousel=True,
                supports_video=True,
                aspect_ratios=["16:9", "9:16", "1:1", "4:5"]
            ),
            SocialPlatform.TWITTER: PlatformSpecs(
                name="Twitter/X",
                image_dimensions={
                    "post": (1200, 675),
                    "header": (1500, 500),
                    "card": (1200, 628)
                },
                text_limits={
                    "tweet": 280,
                    "thread": 280  # per tweet
                },
                hashtag_limit=10,
                supports_carousel=False,
                supports_video=True,
                aspect_ratios=["16:9", "1:1", "2:1"]
            ),
            SocialPlatform.LINKEDIN: PlatformSpecs(
                name="LinkedIn",
                image_dimensions={
                    "post": (1200, 627),
                    "article": (1200, 627),
                    "company": (1536, 768),
                    "personal": (1584, 396)
                },
                text_limits={
                    "post": 3000,
                    "article": 125000
                },
                hashtag_limit=5,
                supports_carousel=True,
                supports_video=True,
                aspect_ratios=["1.91:1", "1:1", "4:5"]
            ),
            SocialPlatform.PINTEREST: PlatformSpecs(
                name="Pinterest",
                image_dimensions={
                    "pin": (1000, 1500),
                    "square": (1000, 1000),
                    "story": (1080, 1920)
                },
                text_limits={
                    "description": 500,
                    "title": 100
                },
                hashtag_limit=20,
                supports_carousel=False,
                supports_video=True,
                aspect_ratios=["2:3", "1:1", "9:16"]
            ),
            SocialPlatform.TIKTOK: PlatformSpecs(
                name="TikTok",
                image_dimensions={
                    "video": (1080, 1920),
                    "photo": (1080, 1920)
                },
                text_limits={
                    "caption": 2200,
                    "comment": 150
                },
                hashtag_limit=100,
                supports_carousel=True,
                supports_video=True,
                aspect_ratios=["9:16", "1:1", "16:9"]
            )
        }
    
    async def generate_posts(
        self,
        analysis_data: Dict[str, Any],
        asset_ids: List[int],
        platforms: List[SocialPlatform],
        context: Dict[str, Any] = None
    ) -> List[SocialMediaPost]:
        """Generate optimized posts for multiple platforms"""
        
        posts = []
        context = context or {}
        
        for platform in platforms:
            try:
                post = await self.generate_single_post(
                    analysis_data,
                    asset_ids,
                    platform,
                    context
                )
                posts.append(post)
            except Exception as e:
                log.error(f"Failed to generate {platform.value} post: {str(e)}")
                continue
        
        return posts
    
    async def generate_single_post(
        self,
        analysis_data: Dict[str, Any],
        asset_ids: List[int],
        platform: SocialPlatform,
        context: Dict[str, Any] = None
    ) -> SocialMediaPost:
        """Generate a single platform-optimized post"""
        
        specs = self.platform_specs[platform]
        context = context or {}
        
        # Extract relevant information from analysis
        image_descriptions = []
        themes = analysis_data.get("marketing_themes", [])
        target_audience = analysis_data.get("target_audience", [])
        
        for img_analysis in analysis_data.get("individual_analyses", []):
            image_descriptions.append({
                "features": img_analysis.get("features", []),
                "type": img_analysis.get("type", "unknown"),
                "quality": img_analysis.get("quality_score", 0.5)
            })
        
        # Generate platform-specific content
        content_prompt = self._build_content_prompt(
            platform,
            specs,
            image_descriptions,
            themes,
            target_audience,
            context
        )
        
        # Generate content using AI
        generated_content = await self.vertex_client.generate_text_response(
            content_prompt,
            max_tokens=1000,
            temperature=0.7
        )
        
        # Parse and format the generated content
        post_content = self._parse_generated_content(
            generated_content,
            platform,
            specs
        )
        
        # Calculate performance score
        performance_score = self._calculate_performance_score(
            post_content,
            platform,
            analysis_data
        )
        
        # Generate post ID
        post_id = f"{platform.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return SocialMediaPost(
            post_id=post_id,
            platform=platform,
            content=post_content,
            asset_ids=asset_ids,
            performance_score=performance_score,
            estimated_reach=self._estimate_reach(performance_score, platform),
            best_posting_times=self._get_optimal_posting_times(platform)
        )
    
    def _build_content_prompt(
        self,
        platform: SocialPlatform,
        specs: PlatformSpecs,
        image_descriptions: List[Dict],
        themes: List[str],
        target_audience: List[str],
        context: Dict[str, Any]
    ) -> str:
        """Build AI prompt for content generation"""
        
        platform_guidelines = {
            SocialPlatform.INSTAGRAM: "Use engaging, visual language. Include relevant hashtags. Create content that encourages engagement and shares.",
            SocialPlatform.FACEBOOK: "Write conversational, community-focused content. Encourage comments and shares. Use clear calls-to-action.",
            SocialPlatform.TWITTER: "Be concise and witty. Use trending topics and hashtags. Create shareable, quotable content.",
            SocialPlatform.LINKEDIN: "Professional tone, industry insights. Focus on value and expertise. Use business-relevant hashtags.",
            SocialPlatform.PINTEREST: "Focus on inspiration and how-to content. Use descriptive, searchable language. Include relevant keywords.",
            SocialPlatform.TIKTOK: "Trendy, energetic language. Focus on entertainment and authenticity. Use popular sounds and hashtags."
        }
        
        prompt = f"""Create a {platform.value} post for the following images:

Image Analysis:
{json.dumps(image_descriptions, indent=2)}

Marketing Themes: {', '.join(themes)}
Target Audience: {', '.join(target_audience)}
Business Context: {context.get('business_type', 'general business')}

Platform Guidelines for {specs.name}:
- {platform_guidelines[platform]}
- Caption limit: {specs.text_limits.get('caption', specs.text_limits.get('post', 280))} characters
- Hashtag limit: {specs.hashtag_limit} hashtags
- Supports carousel: {specs.supports_carousel}

Please generate:
1. An engaging caption that fits the platform's style and character limits
2. Relevant hashtags (max {specs.hashtag_limit})
3. 2-3 engagement hooks (questions, calls-to-action, etc.)
4. A clear call-to-action
5. Image layout recommendations (carousel, single image, etc.)

Format your response as JSON:
{{
    "caption": "engaging caption text",
    "hashtags": ["hashtag1", "hashtag2", "hashtag3"],
    "engagement_hooks": ["hook 1", "hook 2"],
    "call_to_action": "clear CTA",
    "image_layout": "recommended layout",
    "content_strategy": "brief explanation of approach"
}}"""
        
        return prompt
    
    def _parse_generated_content(
        self,
        generated_content: str,
        platform: SocialPlatform,
        specs: PlatformSpecs
    ) -> PostContent:
        """Parse AI-generated content into structured format"""
        
        try:
            # Try to parse as JSON first
            if generated_content.strip().startswith('{'):
                content_data = json.loads(generated_content)
            else:
                # Fallback parsing for non-JSON responses
                content_data = self._parse_freeform_content(generated_content)
            
            # Validate and truncate caption if needed
            caption = content_data.get("caption", "")
            max_caption_length = specs.text_limits.get('caption', specs.text_limits.get('post', 280))
            if len(caption) > max_caption_length:
                caption = caption[:max_caption_length-3] + "..."
            
            # Limit hashtags
            hashtags = content_data.get("hashtags", [])[:specs.hashtag_limit]
            
            # Extract other elements
            engagement_hooks = content_data.get("engagement_hooks", [])
            call_to_action = content_data.get("call_to_action")
            
            # Generate image configuration
            image_config = self._generate_image_config(
                platform,
                specs,
                content_data.get("image_layout", "single")
            )
            
            return PostContent(
                platform=platform,
                caption=caption,
                hashtags=hashtags,
                image_config=image_config,
                engagement_hooks=engagement_hooks,
                call_to_action=call_to_action,
                scheduling_suggestions=self._get_optimal_posting_times(platform)
            )
            
        except Exception as e:
            log.error(f"Failed to parse generated content: {str(e)}")
            # Return basic content as fallback
            return PostContent(
                platform=platform,
                caption="Check out these amazing images!",
                hashtags=[f"#{platform.value}"],
                image_config=self._generate_image_config(platform, specs, "single"),
                engagement_hooks=["What do you think?"],
                call_to_action="Follow for more!"
            )
    
    def _parse_freeform_content(self, content: str) -> Dict[str, Any]:
        """Parse non-JSON formatted content"""
        
        lines = content.split('\n')
        parsed = {
            "caption": "",
            "hashtags": [],
            "engagement_hooks": [],
            "call_to_action": None
        }
        
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Identify sections
            if "caption:" in line.lower():
                current_section = "caption"
                parsed["caption"] = line.split(":", 1)[1].strip()
            elif "hashtag" in line.lower():
                current_section = "hashtags"
                # Extract hashtags from line
                hashtags = re.findall(r'#\w+', line)
                parsed["hashtags"].extend([h[1:] for h in hashtags])  # Remove # symbol
            elif "hook" in line.lower() or "engagement" in line.lower():
                current_section = "hooks"
            elif "call" in line.lower() and "action" in line.lower():
                current_section = "cta"
                parsed["call_to_action"] = line.split(":", 1)[1].strip() if ":" in line else line
            else:
                # Continue current section
                if current_section == "caption" and not parsed["caption"]:
                    parsed["caption"] = line
                elif current_section == "hooks":
                    parsed["engagement_hooks"].append(line)
        
        return parsed
    
    def _generate_image_config(
        self,
        platform: SocialPlatform,
        specs: PlatformSpecs,
        layout: str
    ) -> Dict[str, Any]:
        """Generate image configuration for the platform"""
        
        # Determine best dimensions based on platform and layout
        if platform == SocialPlatform.INSTAGRAM:
            if layout == "carousel":
                dimensions = specs.image_dimensions["square"]
            elif layout == "story":
                dimensions = specs.image_dimensions["story"]
            else:
                dimensions = specs.image_dimensions["square"]
        else:
            # Use default post dimensions for other platforms
            dimensions = list(specs.image_dimensions.values())[0]
        
        return {
            "layout": layout,
            "dimensions": dimensions,
            "aspect_ratio": f"{dimensions[0]}:{dimensions[1]}",
            "supports_carousel": specs.supports_carousel,
            "recommended_format": "JPEG" if "photo" in layout else "MP4"
        }
    
    def _calculate_performance_score(
        self,
        content: PostContent,
        platform: SocialPlatform,
        analysis_data: Dict[str, Any]
    ) -> float:
        """Calculate expected performance score for the post"""
        
        score = 0.5  # Base score
        
        # Caption quality (length, engagement elements)
        if content.caption:
            if len(content.caption) > 50:  # Substantial content
                score += 0.1
            if any(hook in content.caption.lower() for hook in ['?', 'what', 'how', 'why']):
                score += 0.1  # Engagement questions
        
        # Hashtag optimization
        if content.hashtags:
            optimal_hashtag_count = min(len(content.hashtags), self.platform_specs[platform].hashtag_limit)
            if platform == SocialPlatform.INSTAGRAM and optimal_hashtag_count >= 5:
                score += 0.1
            elif platform == SocialPlatform.LINKEDIN and optimal_hashtag_count <= 5:
                score += 0.1
            elif platform == SocialPlatform.TWITTER and optimal_hashtag_count <= 3:
                score += 0.1
        
        # Call-to-action presence
        if content.call_to_action:
            score += 0.1
        
        # Image quality from analysis
        avg_quality = analysis_data.get("overall_confidence", 0.5)
        score += (avg_quality - 0.5) * 0.4  # Scale quality impact
        
        return min(max(score, 0.0), 1.0)  # Clamp between 0 and 1
    
    def _estimate_reach(self, performance_score: float, platform: SocialPlatform) -> int:
        """Estimate potential reach based on performance score and platform"""
        
        # Base reach estimates per platform (very rough estimates)
        base_reach = {
            SocialPlatform.INSTAGRAM: 500,
            SocialPlatform.FACEBOOK: 300,
            SocialPlatform.TWITTER: 200,
            SocialPlatform.LINKEDIN: 150,
            SocialPlatform.PINTEREST: 400,
            SocialPlatform.TIKTOK: 1000
        }
        
        platform_base = base_reach.get(platform, 300)
        return int(platform_base * (0.5 + performance_score))
    
    def _get_optimal_posting_times(self, platform: SocialPlatform) -> List[str]:
        """Get optimal posting times for the platform"""
        
        optimal_times = {
            SocialPlatform.INSTAGRAM: ["11:00 AM", "2:00 PM", "5:00 PM"],
            SocialPlatform.FACEBOOK: ["9:00 AM", "1:00 PM", "3:00 PM"],
            SocialPlatform.TWITTER: ["8:00 AM", "12:00 PM", "7:00 PM"],
            SocialPlatform.LINKEDIN: ["8:00 AM", "12:00 PM", "5:00 PM"],
            SocialPlatform.PINTEREST: ["8:00 PM", "10:00 PM", "11:00 PM"],
            SocialPlatform.TIKTOK: ["6:00 AM", "10:00 AM", "7:00 PM"]
        }
        
        return optimal_times.get(platform, ["12:00 PM", "3:00 PM", "6:00 PM"])