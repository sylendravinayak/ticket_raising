import asyncio
from sqlalchemy import text
from src.data.clients.postgres_client import engine

async def cleanup():
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS roles CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS refresh_tokens CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS contact_mode_enum"))
        await conn.execute(text("DROP TYPE IF EXISTS userrole"))
    await engine.dispose()
    print("Cleaned up.")

asyncio.run(cleanup())
