import json
import logging
from typing import Any

from src.core.redis import redis_client

logger = logging.getLogger(__name__)


class CacheManager:
    @staticmethod
    async def get(key: str) -> Any | None:
        """Получить данные из кэша"""
        data = await redis_client.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return data
        return None

    @staticmethod
    async def set(key: str, value: Any, ttl: int) -> None:
        """Сохранить данные в кэш с TTL (в секундах)"""
        await redis_client.setex(
            key, ttl, json.dumps(value, ensure_ascii=False)
        )

    @staticmethod
    async def delete(key: str) -> None:
        """Удалить конкретный ключ"""
        await redis_client.delete(key)

    @staticmethod
    async def delete_pattern(pattern: str) -> int:
        """
        Безопасное удаление ключей по паттерну через SCAN.
        Возвращает количество удаленных ключей.
        """
        deleted_count = 0
        cursor = 0
        while True:
            cursor, keys = await redis_client.scan(
                cursor, match=pattern, count=100
            )
            if keys:
                deleted_count += await redis_client.delete(*keys)
            if cursor == 0:
                break
        if deleted_count > 0:
            logger.info(
                "Инвалидировано %s ключей по паттерну %s",
                deleted_count,
                pattern,
            )
        return deleted_count


cache = CacheManager()
