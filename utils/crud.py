from sqlalchemy.ext.asyncio import AsyncSession
from auth.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_user(db: AsyncSession, email: str, password: str, is_superuser: bool = False, is_active: bool = True):
    hashed_password = pwd_context.hash(password)

    db_user = User(
        email=email,
        hashed_password=hashed_password,
        is_superuser=is_superuser,
        is_active=is_active
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    return db_user
