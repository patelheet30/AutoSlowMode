import logging
import os

import arc
import hikari
import toolbox
from dotenv import load_dotenv

load_dotenv()


logger = logging.getLogger(__name__)

bot = hikari.GatewayBot(token=os.environ["TOKEN"], logs="TRACE_HIKARI")

client = arc.GatewayClient(bot)


@bot.listen()
async def on_startup(event: hikari.StartedEvent) -> None:
    logger.info(f"Bot is starting up... {bot.get_me()}")
    logger.info(f"Connected to {len(bot.cache.get_unavailable_guilds_view())} guilds")


@client.include
@arc.slash_command("testing", "Testing command")
async def testing(ctx: arc.GatewayContext) -> None:
    perms = toolbox.calculate_permissions(ctx.member, ctx.channel)
    await ctx.respond(f"Permissions for {ctx.member}: {perms}\n")


if __name__ == "__main__":
    bot.run()
