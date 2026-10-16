from typing import TypeVar

from .base import BaseModel
from .batch import Batch
from .product import Product
from .webhook import WebhookDelivery, WebhookSubscription
from .work_center import WorkCenter

MODEL = TypeVar("MODEL", bound=BaseModel)

TypeModel = type[MODEL]
