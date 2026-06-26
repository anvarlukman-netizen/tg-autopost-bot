from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import settings

_scheduler: AsyncIOScheduler | None = None


def create_scheduler() -> AsyncIOScheduler:
    global _scheduler
    _scheduler = AsyncIOScheduler(
        timezone=settings.TIMEZONE,
        job_defaults={"misfire_grace_time": 600},  # fire even if up to 10 min late
    )
    return _scheduler


def get_scheduler() -> AsyncIOScheduler:
    assert _scheduler is not None, "Scheduler not initialized"
    return _scheduler
