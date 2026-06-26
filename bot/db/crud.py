from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.db.models import Channel, GlobalSettings, Post, PostButton, PostMedia, PostStatus


# ── Channels ──────────────────────────────────────────────────────────────────

async def get_channels(session: AsyncSession) -> list[Channel]:
    result = await session.execute(select(Channel).where(Channel.is_active == True))
    return list(result.scalars().all())


async def get_channel_by_tg_id(session: AsyncSession, tg_id: int) -> Channel | None:
    result = await session.execute(select(Channel).where(Channel.tg_id == tg_id))
    return result.scalar_one_or_none()


async def get_channel(session: AsyncSession, channel_id: int) -> Channel | None:
    return await session.get(Channel, channel_id)


async def create_channel(session: AsyncSession, tg_id: int, title: str, username: str | None) -> Channel:
    channel = Channel(tg_id=tg_id, title=title, username=username)
    session.add(channel)
    await session.commit()
    await session.refresh(channel)
    return channel


async def delete_channel(session: AsyncSession, channel_id: int) -> None:
    channel = await session.get(Channel, channel_id)
    if channel:
        await session.delete(channel)
        await session.commit()


# ── Posts ─────────────────────────────────────────────────────────────────────

async def create_post(session: AsyncSession, channel_id: int) -> Post:
    post = Post(channel_id=channel_id, status=PostStatus.draft)
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return post


async def get_post(session: AsyncSession, post_id: int) -> Post | None:
    result = await session.execute(
        select(Post)
        .where(Post.id == post_id)
        .options(selectinload(Post.media), selectinload(Post.buttons), selectinload(Post.channel))
    )
    return result.scalar_one_or_none()


async def get_scheduled_posts(session: AsyncSession) -> list[Post]:
    result = await session.execute(
        select(Post)
        .where(Post.status == PostStatus.scheduled)
        .options(selectinload(Post.channel))
        .order_by(Post.scheduled_at)
    )
    return list(result.scalars().all())


async def update_post_text(session: AsyncSession, post_id: int, text: str) -> None:
    await session.execute(update(Post).where(Post.id == post_id).values(text=text))
    await session.commit()


async def update_post_footer(session: AsyncSession, post_id: int, footer: str | None) -> None:
    await session.execute(update(Post).where(Post.id == post_id).values(footer=footer))
    await session.commit()


async def update_post_options(
    session: AsyncSession,
    post_id: int,
    silent: bool,
    pin: bool,
    auto_delete: int | None,
    disable_web_preview: bool,
) -> None:
    await session.execute(
        update(Post).where(Post.id == post_id).values(
            silent=silent,
            pin_after_publish=pin,
            auto_delete_after=auto_delete,
            disable_web_preview=disable_web_preview,
        )
    )
    await session.commit()


async def schedule_post(session: AsyncSession, post_id: int, scheduled_at: datetime) -> None:
    await session.execute(
        update(Post).where(Post.id == post_id).values(
            status=PostStatus.scheduled,
            scheduled_at=scheduled_at,
        )
    )
    await session.commit()


async def mark_published(session: AsyncSession, post_id: int, tg_message_id: int) -> None:
    await session.execute(
        update(Post).where(Post.id == post_id).values(
            status=PostStatus.published,
            published_at=datetime.utcnow(),
            tg_message_id=tg_message_id,
        )
    )
    await session.commit()


async def mark_failed(session: AsyncSession, post_id: int) -> None:
    await session.execute(update(Post).where(Post.id == post_id).values(status=PostStatus.failed))
    await session.commit()


async def cancel_post(session: AsyncSession, post_id: int) -> None:
    await session.execute(update(Post).where(Post.id == post_id).values(status=PostStatus.cancelled))
    await session.commit()


async def delete_post(session: AsyncSession, post_id: int) -> None:
    post = await session.get(Post, post_id)
    if post:
        await session.delete(post)
        await session.commit()


# ── Media ─────────────────────────────────────────────────────────────────────

async def add_media(session: AsyncSession, post_id: int, media_type: str, file_id: str, position: int) -> None:
    media = PostMedia(post_id=post_id, media_type=media_type, file_id=file_id, position=position)
    session.add(media)
    await session.commit()


async def clear_media(session: AsyncSession, post_id: int) -> None:
    post = await get_post(session, post_id)
    if post:
        for m in post.media:
            await session.delete(m)
        await session.commit()


# ── Buttons ───────────────────────────────────────────────────────────────────

async def set_buttons(session: AsyncSession, post_id: int, buttons: list[dict]) -> None:
    post = await get_post(session, post_id)
    if post:
        for b in post.buttons:
            await session.delete(b)
    for btn in buttons:
        session.add(PostButton(
            post_id=post_id,
            row=btn["row"],
            col=btn["col"],
            text=btn["text"],
            url=btn["url"],
        ))
    await session.commit()


# ── Global Settings ───────────────────────────────────────────────────────────

async def get_settings(session: AsyncSession) -> GlobalSettings:
    s = await session.get(GlobalSettings, 1)
    if s is None:
        s = GlobalSettings(id=1)
        session.add(s)
        await session.commit()
        await session.refresh(s)
    return s


async def update_settings(session: AsyncSession, **kwargs) -> None:
    s = await get_settings(session)
    for key, value in kwargs.items():
        setattr(s, key, value)
    await session.commit()
