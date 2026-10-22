from enum import StrEnum


class WebhookEventType(StrEnum):
    """Допустимые типы событий для вебхуков"""

    BATCH_CREATED = "batch_created"
    BATCH_UPDATED = "batch_updated"
    BATCH_CLOSED = "batch_closed"
    PRODUCT_AGGREGATED = "product_aggregated"
    REPORT_GENERATED = "report_generated"
    IMPORT_COMPLETED = "import_completed"


class DeliveryStatus(StrEnum):
    """Статусы доставки вебхука"""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"
