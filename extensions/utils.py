import logging
import traceback
from typing import Dict, List

import arc
import hikari

logger = logging.getLogger("utils")

plugin = arc.GatewayPlugin("utils")

message_cache: Dict[int, List[float]] = {}


def calculate_message_rate(channel_id: int, window_seconds: int = 60) -> float:
    import time

    if channel_id not in message_cache:
        return 0.0

    now = time.time()
    cutoff = now - window_seconds

    message_cache[channel_id] = [ts for ts in message_cache[channel_id] if ts > cutoff]

    return len(message_cache[channel_id]) * (60 / window_seconds)


async def determine_optimal_slowmode(message_rate: float, threshold: int) -> int:
    if message_rate <= threshold:
        return 0
    elif message_rate <= threshold * 1.5:
        return 5
    elif message_rate <= threshold * 2:
        return 10
    elif message_rate <= threshold * 3:
        return 15
    elif message_rate <= threshold * 4:
        return 30
    elif message_rate <= threshold * 5:
        return 60
    elif message_rate <= threshold * 6:
        return 120
    elif message_rate <= threshold * 7:
        return 300
    elif message_rate <= threshold * 8:
        return 600
    else:
        return 900


@plugin.set_error_handler
async def on_error(ctx: arc.GatewayContext, error: Exception) -> None:
    if isinstance(error, hikari.ForbiddenError):
        await ctx.respond(
            "I don't have permission to do that.", flags=hikari.MessageFlag.EPHEMERAL
        )
    elif isinstance(error, hikari.NotFoundError):
        await ctx.respond(
            "The requested resource was not found.", flags=hikari.MessageFlag.EPHEMERAL
        )
    elif isinstance(error, arc.errors.CommandInvokeError):
        logger.error(f"Error in command {ctx.command.name}: {error.__cause__}")
        logger.error(traceback.format_exc())
        await ctx.respond(
            "An error occurred while executing the command.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
    else:
        logger.error(f"Unhandled error: {error}")
        logger.error(traceback.format_exc())
        await ctx.respond(
            "An unexpected error occurred.", flags=hikari.MessageFlag.EPHEMERAL
        )

    raise error


@arc.loader
def loader(client: arc.GatewayClient) -> None:
    client.add_plugin(plugin)


@arc.unloader
def unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(plugin)
