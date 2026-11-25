"""
Вспомогательные функции для расчёта сроков наказаний.
"""
from datetime import datetime, timedelta


def calc_expiry_hours(hours: int) -> datetime:
    return datetime.utcnow() + timedelta(hours=hours)


def calc_expiry_days(days: int) -> datetime:
    return datetime.utcnow() + timedelta(days=days)


def is_ban_active(banned_until: datetime | None, is_banned: bool) -> bool:
    if not is_banned:
        return False
    if banned_until is None:
        return True  # перманентный бан
    return datetime.utcnow() < banned_until
