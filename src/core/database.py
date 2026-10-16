from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import config

engine = create_async_engine(
    config.database_url,
    pool_size=config.DB_POOL_SIZE,
    echo=config.DEBUG,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """
    Dependency для получения async сессии.

    Автоматически коммитит транзакцию при успешном завершении запроса.
    Откатывает при исключении.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def dispose_engine() -> None:
    """
    Закрыть все соединения с БД.

    Вызывается при shutdown приложения.
    """
    await engine.dispose()


AsyncSessionDependency = Annotated[AsyncSession, Depends(get_async_session)]
