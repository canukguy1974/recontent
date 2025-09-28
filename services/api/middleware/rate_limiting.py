"""
Rate Limiting Middleware
Provides credit-based rate limiting for API endpoints that consume AI resources.
"""
from typing import Callable, Optional
from fastapi import Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import functools

from db.models import ActionType, User
from services.api.deps import get_db, get_current_user
from services.api.utils.credits import (
    check_credits_available, 
    consume_credits, 
    InsufficientCreditsError,
    get_credit_status
)
from packages.common.logging import get_logger

log = get_logger("rate-limiting")


def require_credits(action_type: ActionType, cost_override: Optional[int] = None):
    """
    Decorator to require credits for an endpoint.
    
    Usage:
        @require_credits(ActionType.IMAGE_GENERATION)
        def generate_image(...):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies from kwargs
            db: Session = None
            current_user: User = None
            
            # Look for db and current_user in function arguments
            import inspect
            sig = inspect.signature(func)
            
            # Get dependency values
            for param_name, param in sig.parameters.items():
                if param_name in kwargs:
                    if param_name == 'db' or (hasattr(param.default, 'dependency') and param.default.dependency == get_db):
                        db = kwargs[param_name]
                    elif param_name == 'current_user' or (hasattr(param.default, 'dependency') and param.default.dependency == get_current_user):
                        current_user = kwargs[param_name]
            
            if not db or not current_user:
                raise HTTPException(500, "Rate limiting dependencies not available")
            
            # Check if credits are available
            if not check_credits_available(db, current_user.id, action_type):
                credit_status = get_credit_status(db, current_user.id)
                raise HTTPException(
                    402,  # Payment Required
                    detail={
                        "error": "insufficient_credits",
                        "message": f"Not enough credits for {action_type.value}",
                        "credit_status": credit_status
                    }
                )
            
            # Pre-consume credits (will be rolled back if operation fails)
            try:
                usage_log = consume_credits(db, current_user.id, action_type)
                db.commit()
                
                # Add usage_log to kwargs so the endpoint can access it
                if 'usage_log' in sig.parameters:
                    kwargs['usage_log'] = usage_log
                
            except InsufficientCreditsError as e:
                db.rollback()
                credit_status = get_credit_status(db, current_user.id)
                raise HTTPException(
                    402,
                    detail={
                        "error": "insufficient_credits",
                        "message": str(e),
                        "credit_status": credit_status
                    }
                )
            except Exception as e:
                db.rollback()
                log.error(f"Failed to consume credits: {e}")
                raise HTTPException(500, "Credit system error")
            
            # Call the actual endpoint
            try:
                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                return result
                
            except Exception as e:
                # If the endpoint failed, we might want to refund credits
                # This depends on the type of failure - for now, we'll leave credits consumed
                # as the user did initiate the request
                log.warning(f"Endpoint failed after consuming credits: {e}")
                raise
        
        return wrapper
    return decorator


class RateLimitingMiddleware:
    """
    Middleware to add rate limiting headers to all responses.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        request = Request(scope, receive)
        
        # Only add headers to API endpoints that require auth
        path = request.url.path
        if not path.startswith("/api/") or path in ["/api/health", "/api/webhooks/stripe"]:
            return await self.app(scope, receive, send)
        
        # Create a custom send function to add headers
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                
                # Try to get user's credit status if authenticated
                try:
                    # This is a simplified approach - in a real implementation,
                    # you might want to cache this or get it from the request context
                    auth_header = request.headers.get("Authorization")
                    if auth_header:
                        # Add rate limiting headers
                        headers[b"X-RateLimit-Policy"] = b"credits"
                        # Note: In production, you'd want to get actual values from the database
                        # headers[b"X-RateLimit-Remaining"] = str(remaining_credits).encode()
                        # headers[b"X-RateLimit-Reset"] = str(reset_timestamp).encode()
                
                except Exception:
                    # If we can't get credit info, just skip the headers
                    pass
                
                message["headers"] = list(headers.items())
            
            await send(message)
        
        return await self.app(scope, receive, send_with_headers)


# Convenience functions for common rate limiting patterns
def require_image_generation_credits():
    """Require credits for image generation (2 credits)"""
    return require_credits(ActionType.IMAGE_GENERATION)

def require_image_editing_credits():
    """Require credits for image editing (1 credit)"""
    return require_credits(ActionType.IMAGE_EDITING)

def require_content_generation_credits():
    """Require credits for content generation (1 credit)"""
    return require_credits(ActionType.CONTENT_GENERATION)

def require_post_combination_credits():
    """Require credits for post combination (3 credits)"""
    return require_credits(ActionType.POST_COMBINATION)

def require_social_posts_credits():
    """Require credits for social media post generation (1 credit)"""
    return require_credits(ActionType.SOCIAL_POSTS)