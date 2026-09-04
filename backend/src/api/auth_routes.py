import datetime
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response
from pydantic import BaseModel, EmailStr, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger("controlcold.auth")

from ..database.db import get_db
from ..database.models import User, RefreshToken, get_blind_index
from ..security.auth import (
    hash_password,
    verify_password,
    generate_verification_code,
    create_auth_token,
    decode_auth_token,
    send_email_verification,
    generate_refresh_token_string
)
from ..security.rate_limit import limiter

router = APIRouter(prefix="/api/auth", tags=["Autenticação"])

# Modelos Pydantic para requisições
class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str
    password: str
    phone: Optional[str] = None

class VerifyRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str
    code: str

class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    refresh_token: str

class LoginRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str
    password: str

class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str

class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str
    code: str
    new_password: str

async def get_current_user(request: Request, authorization: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)) -> User:
    """Dependency para obter o usuário logado via Cookie HttpOnly ou Bearer Token"""
    token = request.cookies.get("access_token")
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        
    if not token:
        raise HTTPException(status_code=401, detail="Autenticação requerida (Cookie ou Header ausentes)")
    
    payload = decode_auth_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Sessão expirada ou token inválido")
    
    user = await db.get(User, payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return user

@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Cadastro de nova conta com envio de código de 6 dígitos para confirmação"""
    email_clean = payload.email.strip().lower()
    blind_index = get_blind_index(email_clean)
    
    # Verifica se usuário já existe
    existing = await db.execute(select(User).where(User.email == blind_index))
    user = existing.scalar_one_or_none()
    
    code = generate_verification_code()
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    pwd_hash = hash_password(payload.password)

    if user:
        if user.is_verified:
            raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado e verificado.")
        # Se cadastrou mas não verificou, atualiza código e senha
        user.password_hash = pwd_hash
        user.phone = payload.phone
        user.verification_code = code
        user.code_expires_at = expires_at
    else:
        user = User(
            raw_email=email_clean,
            phone=payload.phone,
            password_hash=pwd_hash,
            is_verified=False,
            verification_code=code,
            code_expires_at=expires_at,
            role="operator"
        )
        db.add(user)

    await db.commit()
    success, msg = send_email_verification(email_clean, code, "confirmação de cadastro")
    if not success:
        logger.warning(f"Falha no envio de e-mail para {email_clean}: {msg}")
        return {
            "success": True,
            "message": f"Conta criada! Porém houve falha no envio do e-mail: {msg}",
            "email": email_clean
        }

    return {
        "success": True,
        "message": f"Código de 6 dígitos enviado para {email_clean}! Verifique sua caixa de entrada (e pasta de spam).",
        "email": email_clean
    }

@router.post("/verify")
@limiter.limit("5/minute")
async def verify_code(request: Request, response: Response, payload: VerifyRequest, db: AsyncSession = Depends(get_db)):
    """Valida o código de 6 dígitos e ativa a conta"""
    email_clean = payload.email.strip().lower()
    blind_index = get_blind_index(email_clean)
    result = await db.execute(select(User).where(User.email == blind_index))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    if not user.verification_code or user.verification_code != payload.code.strip():
        raise HTTPException(status_code=400, detail="Código incorreto. Verifique os 6 dígitos digitados.")

    if user.code_expires_at and user.code_expires_at < datetime.datetime.utcnow():
        raise HTTPException(status_code=400, detail="Código expirado. Solicite um novo código de verificação.")

    # Ativa conta e limpa código
    user.is_verified = True
    user.verification_code = None
    user.code_expires_at = None
    await db.commit()

    token = create_auth_token(user.id, user.email, user.role)
    refresh_token_str = generate_refresh_token_string()
    refresh_record = RefreshToken(
        token=refresh_token_str,
        user_id=user.id,
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7)
    )
    db.add(refresh_record)
    await db.commit()

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True, 
        samesite="lax",
        max_age=900
    )

    return {
        "success": True,
        "message": "Conta verificada e ativada com sucesso!",
        "refresh_token": refresh_token_str,
        "user": user.to_dict()
    }

@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, response: Response, payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Autentica usuário e retorna JWT se a conta já estiver verificada"""
    email_clean = payload.email.strip().lower()
    blind_index = get_blind_index(email_clean)
    result = await db.execute(select(User).where(User.email == blind_index))
    user = result.scalar_one_or_none()

    if not user or not verify_password(user.password_hash, payload.password):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")

    if not user.is_verified:
        # Gera novo código de verificação caso a conta não tenha sido verificada ainda
        code = generate_verification_code()
        user.verification_code = code
        user.code_expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
        await db.commit()
        success, msg = send_email_verification(email_clean, code, "confirmação de conta")
        status_msg = f"Sua conta ainda não foi verificada. Enviamos um novo código de 6 dígitos para {email_clean}."
        if not success:
            status_msg = f"Sua conta ainda não foi ativada. Falha no envio do e-mail: {msg}"
        return {
            "success": False,
            "requires_verification": True,
            "message": status_msg,
            "email": email_clean
        }

    token = create_auth_token(user.id, user.raw_email, user.role)
    refresh_token_str = generate_refresh_token_string()
    refresh_record = RefreshToken(
        token=refresh_token_str,
        user_id=user.id,
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7)
    )
    db.add(refresh_record)
    await db.commit()

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True, 
        samesite="lax",
        max_age=900
    )

    return {
        "success": True,
        "refresh_token": refresh_token_str,
        "user": user.to_dict()
    }

@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Gera código de 6 dígitos para redefinição de senha"""
    email_clean = payload.email.strip().lower()
    blind_index = get_blind_index(email_clean)
    result = await db.execute(select(User).where(User.email == blind_index))
    user = result.scalar_one_or_none()

    if not user:
        # Por segurança, não confirmamos explicitamente se o e-mail existe
        return {
            "success": True,
            "message": "Se o e-mail estiver cadastrado, um código de recuperação foi enviado."
        }

    code = generate_verification_code()
    user.verification_code = code
    user.code_expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    await db.commit()

    success, msg = send_email_verification(email_clean, code, "recuperação de senha")
    status_msg = f"Código de recuperação de 6 dígitos enviado para {email_clean}. Verifique sua caixa de entrada e spam."
    if not success:
        status_msg = f"Falha ao enviar e-mail de recuperação: {msg}"

    return {
        "success": True,
        "message": status_msg,
        "email": email_clean
    }

@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Redefine a senha após validação do código de 6 dígitos"""
    email_clean = payload.email.strip().lower()
    blind_index = get_blind_index(email_clean)
    result = await db.execute(select(User).where(User.email == blind_index))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    if not user.verification_code or user.verification_code != payload.code.strip():
        raise HTTPException(status_code=400, detail="Código incorreto. Verifique os 6 dígitos digitados.")

    if user.code_expires_at and user.code_expires_at < datetime.datetime.utcnow():
        raise HTTPException(status_code=400, detail="Código expirado. Solicite uma nova recuperação.")

    user.password_hash = hash_password(payload.new_password)
    user.verification_code = None
    user.code_expires_at = None
    user.is_verified = True
    await db.commit()

    return {
        "success": True,
        "message": "Senha redefinida com sucesso! Você já pode realizar login com sua nova senha."
    }

@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """Retorna dados do usuário autenticado atual"""
    return user.to_dict()
@router.post("/refresh")
async def refresh_access_token(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Renova o token de acesso (curta duração) usando um Refresh Token válido."""
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == payload.refresh_token))
    rt = result.scalar_one_or_none()

    if not rt or rt.is_revoked or rt.expires_at < datetime.datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh Token inválido ou expirado.")

    user = await db.get(User, rt.user_id)
    if not user or not user.is_verified:
        raise HTTPException(status_code=401, detail="Usuário inválido ou não verificado.")

    new_access_token = create_auth_token(user.id, user.raw_email, user.role)
    return {
        "success": True,
        "token": new_access_token
    }

@router.post("/logout")
async def logout(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Revoga o Refresh Token para encerrar a sessão."""
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == payload.refresh_token))
    rt = result.scalar_one_or_none()
    
    if rt:
        rt.is_revoked = True
        await db.commit()

    return {"success": True, "message": "Sessão encerrada com sucesso."}
