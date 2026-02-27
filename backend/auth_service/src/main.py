from src.api.rest.app import create_app
from src.data.clients.postgres_client import engine
from src.data.models.postgres.base import Base

from src.data.models.postgres.user import User
from src.data.models.postgres.role import Role


app = create_app()


@app.on_event("startup")
async def on_startup():
    print(Base.metadata.tables.keys())  # debug
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)