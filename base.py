"""
Движок и фабрика сессий SQLAlchemy (async).
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

import config


class Base(DeclarativeBase):
    pass


engine = create_async_engine(config.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_models() -> None:
    """Создать таблицы, если их ещё нет. Для прод-окружения лучше использовать alembic."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
