"""
Проверка прав доступа по ролям.
Иерархия: user < moderator < senior_moderator < administrator < owner
"""
from models import Role

_HIERARCHY = {
    Role.USER: 0,
    Role.MODERATOR: 1,
    Role.SENIOR_MODERATOR: 2,
    Role.ADMINISTRATOR: 3,
    Role.OWNER: 4,
}


def has_at_least(role: Role, required: Role) -> bool:
    return _HIERARCHY[role] >= _HIERARCHY[required]


def is_moderator(role: Role) -> bool:
    return has_at_least(role, Role.MODERATOR)


def can_manage_moderators(role: Role) -> bool:
    return has_at_least(role, Role.ADMINISTRATOR)


def can_punish(role: Role) -> bool:
    return has_at_least(role, Role.MODERATOR)
