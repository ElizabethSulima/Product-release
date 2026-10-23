import hashlib
import hmac
import json
from typing import Any


def generate_signature(payload: dict[str, Any], secret_key: str) -> str:
    """
    Генерация HMAC-SHA256 подписи для webhook payload.

    Args:
        payload: Словарь с данными события (будет сериализован в JSON)
        secret_key: Секретный ключ подписки

    """
    payload_bytes = json.dumps(
        payload, sort_keys=True, ensure_ascii=False
    ).encode("utf-8")
    secret_bytes = secret_key.encode("utf-8")

    signature = hmac.new(
        secret_bytes, payload_bytes, hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


def verify_signature(
    payload: dict[str, Any], secret_key: str, signature: str
) -> bool:
    """
    Верификация подписи webhook на стороне получателя.

    Args:
        payload: Полученный payload
        secret_key: Секретный ключ
        signature: Подпись из заголовка X-Webhook-Signature

    """
    expected = generate_signature(payload, secret_key)
    return hmac.compare_digest(expected, signature)
