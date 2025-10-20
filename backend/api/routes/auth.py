"""
HeartBeat Engine - Authentication Routes
Montreal Canadiens Advanced Analytics Assistant

Authentication endpoints for the HeartBeat Engine API.
"""

from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timedelta
import base64
import logging

from ..models.requests import LoginRequest
from ..models.responses import AuthResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

# Simple user database (same as main.py for consistency)
USERS_DB = {
    "coach_martin": {
        "password": "coach2024",
        "name": "Martin St-Louis",
        "role": "coach",
        "email": "martin@canadiens.com",
        "team_access": ["MTL"]
    },
    "analyst_hughes": {
        "password": "analyst2024", 
        "name": "Kent Hughes",
        "role": "analyst",
        "email": "kent@canadiens.com",
        "team_access": ["MTL"]
    },
    "player_suzuki": {
        "password": "player2024",
        "name": "Nick Suzuki", 
        "role": "player",
        "email": "nick@canadiens.com",
        "team_access": ["MTL"]
    },
    "scout_lapointe": {
        "password": "scout2024",
        "name": "Martin Lapointe",
        "role": "scout", 
        "email": "martin.lapointe@canadiens.com",
        "team_access": ["MTL"]
    },
    "staff_molson": {
        "password": "staff2024",
        "name": "Geoff Molson",
        "role": "staff",
        "email": "geoff@canadiens.com", 
        "team_access": ["MTL"]
    }
}

@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return access token.
    
    For development, using simple base64 token format.
    In production, use proper JWT tokens with signing.
    """
    
    try:
        # Validate credentials
        user_data = USERS_DB.get(request.username)
        
        if not user_data or user_data["password"] != request.password:
            logger.warning(f"Failed login attempt for username: {request.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Create simple token (username:password base64 encoded)
        # In production, use proper JWT with signing and expiration
        token_data = f"{request.username}:{request.password}"
        access_token = base64.b64encode(token_data.encode()).decode()
        
        # Prepare user info for frontend
        user_info = {
            "username": request.username,
            "name": user_data["name"],
            "role": user_data["role"],
            "email": user_data["email"],
            "team_access": user_data["team_access"]
        }
        
        logger.info(f"Successful login for user: {request.username} ({user_data['role']})")
        
        return AuthResponse(
            success=True,
            access_token=access_token,
            user_info=user_info,
            message="Authentication successful",
            expires_in=3600  # 1 hour
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )

@router.post("/logout")
async def logout():
    """Logout endpoint (for consistency, frontend handles token removal)"""
    return {"success": True, "message": "Logout successful"}

@router.get("/verify")
async def verify_token():
    """Verify token validity (placeholder for future JWT verification)"""
    return {"success": True, "message": "Token verification endpoint"}
