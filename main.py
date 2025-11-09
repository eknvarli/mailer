from fastapi import FastAPI
from auth.routes import router as auth_router
from emails.router import router as email_router
from core.database import Base, engine

app = FastAPI(title="Email Analyzer SaaS")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(auth_router)
app.include_router(email_router)