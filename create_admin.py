import asyncio
from core.database import async_session
from utils.crud import create_user

async def main():
    async with async_session() as db:
        mail = input('Email:')
        password = input('Password:')
        user = await create_user(db, mail, password, True)
        print("Admin user created:", user.email)

asyncio.run(main())
