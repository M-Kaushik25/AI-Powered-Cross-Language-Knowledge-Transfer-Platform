import uuid
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any

from backend.database import get_db, get_utc_now_iso
from backend.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)

router = APIRouter(prefix="/api/auth", tags=["Authentication & Access Control"])

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[str] = "USER"
    preferred_lang: Optional[str] = "en"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest):
    now = get_utc_now_iso()
    assigned_role = req.role if req.role in ["USER", "REVIEWER", "ADMIN"] else "USER"
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (req.email.lower().strip(),))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists."
            )
        
        user_id = str(uuid.uuid4())
        hashed_pwd = hash_password(req.password)
        
        cursor.execute("""
            INSERT INTO users (id, name, email, password_hash, role, preferred_lang, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            req.name.strip(),
            req.email.lower().strip(),
            hashed_pwd,
            assigned_role,
            req.preferred_lang,
            now
        ))
        
        # Create initial default workspace
        space_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO knowledge_spaces (id, user_id, name, description, domain, default_lang, created_at)
            VALUES (?, ?, 'Personal Knowledge Space', 'User workspace for cross-language document exploration', 'cloud_computing', ?, ?)
        """, (space_id, user_id, req.preferred_lang, now))

    token = create_access_token({"sub": user_id, "email": req.email, "role": assigned_role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "name": req.name,
            "email": req.email,
            "role": assigned_role,
            "preferred_lang": req.preferred_lang
        }
    }

@router.post("/login")
def login(req: LoginRequest):
    email_clean = req.email.lower().strip()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email_clean,))
        user = cursor.fetchone()
        
        if not user or not verify_password(req.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"}
            )

    token = create_access_token({
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"]
    })
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "preferred_lang": user["preferred_lang"]
        }
    }

@router.get("/me")
def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns the authenticated user extracted strictly from the JWT Bearer token."""
    return current_user
