from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from auth import schemas, services

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=schemas.Token)
async def login(user_data: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    user = await services.authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = services.generate_token(user.id, user.email)
    return {"access_token": token}
