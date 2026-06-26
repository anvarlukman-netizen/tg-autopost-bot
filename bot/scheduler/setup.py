from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import settings

_scheduler: AsyncIOScheduler | None = None


def create_scheduler() -> AsyncIOScheduler:
    global _scheduler
    db_url = settings.DATABASE_URL.replace("+aiosqlite", "")  # sync URL for APScheduler
    jobstores = {"default": SQLAlchemyJobStore(url=db_url)}
    _scheduler = AsyncIOScheduler(jobstores=jobstores, timezone=settings.TIMEZONE)
    return _scheduler


def get_scheduler() -> AsyncIOScheduler:
    assert _scheduler is not None, "Scheduler not initialized"
    return _scheduler
