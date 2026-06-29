from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from bot.config import settings


def _make_engine():
    url = settings.DATABASE_URL
    kwargs = {"echo": False}
    if url.startswith("postgresql"):
        # asyncpg requires ssl passed via connect_args, not sslmode= in URL
        clean_url = url.split("?")[0]
        kwargs["connect_args"] = {"ssl": "require"}
        return create_async_engine(clean_url, **kwargs)
    return create_async_engine(url, **kwargs)


engine = _make_engine()
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    from bot.db import models  # noqa: F401 — ensure models are registered
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
