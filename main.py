"""
Точка входа Swaston Project bot.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
from base import init_models, async_session
from crud import bootstrap_owner
import handler_start as start
import handler_submission as submission
import handler_moderation as moderation
import handler_reactions as reactions
import handler_catalog as catalog
import handler_profile as profile

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    config.validate()

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(submission.router)
    dp.include_router(moderation.router)
    dp.include_router(reactions.router)
    dp.include_router(catalog.router)
    dp.include_router(profile.router)

    await init_models()

    async with async_session() as session:
        await bootstrap_owner(session, config.OWNER_ID)

    logger.info("Swaston Project bot запущен.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
