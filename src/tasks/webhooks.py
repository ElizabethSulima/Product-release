import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from celery.app.task import Task
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.celery_app import celery_app
from src.data.models.webhook import WebhookDelivery
from src.tasks.aggregation import AsyncSessionLocal
from src.utils.webhook import generate_signature

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=5,
    autoretry_for=(httpx.TimeoutException, httpx.NetworkError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def send_webhook_delivery(self: Task, delivery_id: int) -> dict[str, Any]:
    """
    Отправка webhook с retry-логикой и HMAC-подписью
    """
    try:
        return asyncio.run(_process_delivery(delivery_id, self))
    except Exception as exc:
        logger.error(
            "Ошибка отправки webhook delivery %s: %s", delivery_id, exc
        )
        raise


async def _process_delivery(
    delivery_id: int, task_instance: Task
) -> dict[str, Any]:
    """
    Внутренняя асинхронная логика отправки
    """
    async with AsyncSessionLocal() as session:
        stmt = (
            select(WebhookDelivery)
            .options(selectinload(WebhookDelivery.subscription))
            .where(WebhookDelivery.id == delivery_id)
        )
        result = await session.execute(stmt)
        delivery = result.scalar_one_or_none()

        if delivery is None:
            logger.warning("Delivery %s не найден", delivery_id)
            return {"success": False, "error": "Delivery not found"}

        subscription = delivery.subscription

        if subscription is None or not subscription.is_active:
            delivery.status = "canceled"
            delivery.error_message = "Subscription is inactive or deleted"
            await session.commit()
            return {"success": False, "error": "Subscription inactive"}

        if delivery.attempts >= subscription.retry_count:
            delivery.status = "failed"
            delivery.error_message = "Max retry attempts exceeded"
            await session.commit()
            return {"success": False, "error": "Max retries exceeded"}

        payload: dict[str, Any] = delivery.payload
        signature = generate_signature(payload, subscription.secret_key)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": delivery.event_type,
            "X-Webhook-Delivery": str(delivery.id),
            "X-Webhook-Signature": signature,
            "User-Agent": "ProductionControl-Webhook/1.0",
        }

        delivery.attempts += 1
        await session.flush()

        try:
            async with httpx.AsyncClient(
                timeout=float(subscription.timeout)
            ) as client:
                response = await client.post(
                    subscription.url,
                    json=payload,
                    headers=headers,
                )

            delivery.response_status = response.status_code
            delivery.response_body = response.text[:4000]

            if 200 <= response.status_code < 300:
                delivery.status = "success"
                delivery.delivered_at = datetime.now(UTC)
                delivery.error_message = None
                await session.commit()
                logger.info(
                    "Webhook %s успешно отправлен на %s (status=%s)",
                    delivery.id,
                    subscription.url,
                    response.status_code,
                )
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "attempts": delivery.attempts,
                }
            else:
                error_msg = (
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )
                delivery.error_message = error_msg

                if delivery.attempts >= subscription.retry_count:
                    delivery.status = "failed"
                    await session.commit()
                    return {
                        "success": False,
                        "error": error_msg,
                        "attempts": delivery.attempts,
                    }

                await session.commit()
                countdown = min(2**delivery.attempts * 30, 600)
                logger.warning(
                    "Webhook %s получил статус %s, retry через %s сек",
                    delivery.id,
                    response.status_code,
                    countdown,
                )
                raise task_instance.retry(countdown=countdown)

        except httpx.TimeoutException as exc:
            error_msg = f"Timeout after {subscription.timeout}s"
            delivery.error_message = error_msg

            if delivery.attempts >= subscription.retry_count:
                delivery.status = "failed"
                await session.commit()
                return {"success": False, "error": error_msg}

            await session.commit()
            countdown = min(2**delivery.attempts * 30, 600)
            raise task_instance.retry(countdown=countdown) from exc

        except httpx.NetworkError as exc:
            error_msg = f"Network error: {str(exc)[:200]}"
            delivery.error_message = error_msg

            if delivery.attempts >= subscription.retry_count:
                delivery.status = "failed"
                await session.commit()
                return {"success": False, "error": error_msg}

            await session.commit()
            countdown = min(2**delivery.attempts * 30, 600)
            raise task_instance.retry(countdown=countdown) from exc
