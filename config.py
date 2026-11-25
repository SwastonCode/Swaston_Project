"""
Конфигурация проекта. Все значения читаются из переменных окружения —
никогда не хранить токены и ID прямо в коде.
"""
import os


def _env_int(name: str, default: int | None = None) -> int | None:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


# --- Telegram ---
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# ID публичного канала (например -1001234567890) или @username канала
CHANNEL_ID: str = os.getenv("CHANNEL_ID", "")

# ID закрытой группы модераторов
MOD_GROUP_ID: int | None = _env_int("MOD_GROUP_ID")

# Telegram ID владельца проекта (бутстрапится как Owner при первом запуске)
OWNER_ID: int | None = _env_int("OWNER_ID")

# --- База данных ---
# По умолчанию — локальный SQLite для разработки.
# На проде задать DATABASE_URL вида:
#   postgresql+asyncpg://user:password@host:5432/dbname
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./swaston.db")

# --- Лимиты файлов ---
MAX_ARCHIVE_SIZE_MB: int = _env_int("MAX_ARCHIVE_SIZE_MB", 50)
MAX_ZIP_UNCOMPRESSED_MB: int = _env_int("MAX_ZIP_UNCOMPRESSED_MB", 300)
MAX_ZIP_COMPRESSION_RATIO: int = _env_int("MAX_ZIP_COMPRESSION_RATIO", 100)
ALLOWED_ARCHIVE_EXTENSIONS: tuple[str, ...] = (".zip",)

# --- ClamAV (опционально) ---
# Если ClamAV не настроен — сканирование пропускается с пометкой в логах,
# результат сканирования НЕ считается гарантией безопасности (см. п.12 ТЗ).
CLAMAV_HOST: str = os.getenv("CLAMAV_HOST", "")
CLAMAV_PORT: int = _env_int("CLAMAV_PORT", 3310)

# --- Пороги ---
VIRUS_MARKS_THRESHOLD: int = _env_int("VIRUS_MARKS_THRESHOLD", 5)

# --- Пути ---
STORAGE_DIR: str = os.getenv("STORAGE_DIR", "./storage")


def validate() -> None:
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not CHANNEL_ID:
        missing.append("CHANNEL_ID")
    if MOD_GROUP_ID is None:
        missing.append("MOD_GROUP_ID")
    if OWNER_ID is None:
        missing.append("OWNER_ID")
    if missing:
        raise SystemExit(
            "Не заданы обязательные переменные окружения: " + ", ".join(missing) +
            "\nСмотри README.md — раздел 'Переменные окружения'."
        )
