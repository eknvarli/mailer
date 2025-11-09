from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from auth.models import User
from core.security import hash_password, verify_password, create_access_token
from jose import jwt
from core.config import settings

async def create_user(db: AsyncSession, email: str, password: str):
    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def authenticate_user(db: AsyncSession, email: str, password: str):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def generate_token(user_id: int, email: str):
    return create_access_token({"sub": str(user_id), "email": email})

async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.get(User, user_id)
    return result


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.JWTError:
        return {}