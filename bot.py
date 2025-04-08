import asyncio
import logging
import os

import arc
import hikari
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("bot")

if os.name != "nt":
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

bot = hikari.GatewayBot(
    token=os.environ["TOKEN"],
    intents=hikari.Intents.GUILD_MESSAGES,
    # logs="TRACE_HIKARI",
)

client = arc.GatewayClient(bot)


@client.add_startup_hook
async def startup(_: arc.GatewayClient) -> None:
    logger.info(f"Bot is starting up... {bot.get_me()}")
    logger.info(f"Connected to {len(bot.cache.get_unavailable_guilds_view())} guilds")


client.load_extensions_from("extensions")

if __name__ == "__main__":
    bot.run()
