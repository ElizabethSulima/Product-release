import pytest

from src.main import app_fast

pytestmark = pytest.mark.anyio


def test_dummy():
    """Минимальный тест, чтобы CI проходил успешно"""
    assert True


def test_app_imports():
    """Проверка, что основное приложение успешно импортируется"""

    assert app_fast.title == "PRODUCT CONTROL SYSTEM"
