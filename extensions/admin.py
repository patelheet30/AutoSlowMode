import datetime
import logging

import arc
import hikari
import toolbox

from .db import Database
from .utils import calculate_message_rate

logger = logging.getLogger("admin")

plugin = arc.GatewayPlugin(
    "admin", default_permissions=hikari.Permissions.MANAGE_CHANNELS
)


auto_slowmode = plugin.include_slash_group(
    "auto-slowmode", "Configure auto-slowmode settings"
)

channel_group = auto_slowmode.include_subgroup(
    "channel", "Configure auto-slowmode settings for a specific channel"
)


@channel_group.include
@arc.slash_subcommand("enable", "Enable auto-slowmode for a channel")
async def channel_enable(
    ctx: arc.GatewayContext,
    channel: arc.Option[
        hikari.TextableGuildChannel | None,
        arc.ChannelParams("The channel to enable auto-slowmode for"),
    ] = None,
    database: Database = arc.inject(),
) -> None:
    if not channel:
        channel_in = ctx.channel
    else:
        channel_in = channel

    if not ctx.guild_id:
        await ctx.respond("This command can only be used in a server.")
        return

    await database.get_channel_config(channel_in.id, ctx.guild_id)

    await database.update_channel_config(channel_in.id, is_enabled=1)

    embed = hikari.Embed(
        title="Auto Slowmode Enabled",
        description="Auto-slowmode has been enabled for this channel.",
        color=0x00FF00,
    )

    await ctx.respond(embed=embed)
    logger.info(
        f"Auto-slowmode enabled for channel {channel_in.id} by user {ctx.author.id}"
    )


@channel_group.include
@arc.slash_subcommand("disable", "Disable auto-slowmode for a channel")
async def channel_disable(
    ctx: arc.GatewayContext,
    channel: arc.Option[
        hikari.TextableGuildChannel | None,
        arc.ChannelParams("The channel to disable auto-slowmode for"),
    ] = None,
    database: Database = arc.inject(),
) -> None:
    if not channel:
        channel_in = ctx.channel
    else:
        channel_in = channel

    if not ctx.guild_id:
        await ctx.respond("This command can only be used in a server.")
        return

    await database.get_channel_config(channel_in.id, ctx.guild_id)

    await database.update_channel_config(channel_in.id, is_enabled=0)

    await ctx.client.app.rest.edit_channel(channel_in.id, rate_limit_per_user=0)

    embed = hikari.Embed(
        title="Auto Slowmode Disabled",
        description="Auto-slowmode has been disabled for this channel.",
        color=0xFF0000,
    )

    await ctx.respond(embed=embed)
    logger.info(
        f"Auto-slowmode disabled for channel {channel_in.id} by user {ctx.author.id}"
    )


@channel_group.include
@arc.slash_subcommand("threshold", "Set the message rate threshold for a channel")
async def channel_threshold(
    ctx: arc.GatewayContext,
    threshold: arc.Option[
        int,
        arc.IntParams(
            "The message rate threshold (messages per minute)", min=1, max=1000
        ),
    ],
    channel: arc.Option[
        hikari.TextableGuildChannel | None,
        arc.ChannelParams("The channel to set the threshold for"),
    ] = None,
    database: Database = arc.inject(),
) -> None:
    if not channel:
        channel_in = ctx.channel
    else:
        channel_in = channel

    if not ctx.guild_id:
        await ctx.respond("This command can only be used in a server.")
        return

    await database.get_channel_config(channel_in.id, ctx.guild_id)

    await database.update_channel_config(channel_in.id, threshold=threshold)

    embed = hikari.Embed(
        title="Auto Slowmode Threshold Set",
        description=f"Auto-slowmode threshold for {channel_in.mention} has been set to {threshold} messages per minute",
        color=0x00FF00,
    )

    await ctx.respond(embed=embed)
    logger.info(
        f"Auto-slowmode threshold set to {threshold} for channel {channel_in.id} by user {ctx.author.id}"
    )


server_group = auto_slowmode.include_subgroup(
    "server", "Configure auto-slowmode server-wide settings"
)


async def calculate_permissions(
    member: hikari.InteractionMember,
    channel: hikari.PermissibleGuildChannel,
) -> hikari.Permissions:
    permissions = toolbox.members.calculate_permissions(member, channel)
    return permissions


@server_group.include
@arc.slash_subcommand("enable", "Enable auto-slowmode server-wide")
async def server_enable(
    ctx: arc.GatewayContext, database: Database = arc.inject()
) -> None:
    guild_id = ctx.guild_id

    if not guild_id:
        await ctx.respond("This command can only be used in a server.")
        return

    await database.get_guild_config(guild_id)
    await database.update_guild_config(guild_id, is_enabled=1)

    channels = await ctx.client.app.rest.fetch_guild_channels(guild_id)

    for channel in channels:
        if isinstance(channel, hikari.GuildTextChannel):
            logger.info(f"Processing channel {channel.id}")
            await database.get_channel_config(channel.id, guild_id)
            await database.update_channel_config(channel.id, is_enabled=1)

    embed = hikari.Embed(
        title="Auto Slowmode Enabled",
        description="Auto-slowmode has been enabled server-wide.",
        color=0x00FF00,
    )

    await ctx.respond(embed=embed)
    logger.info(f"Auto-slowmode enabled server-wide for guild {guild_id}")


@server_group.include
@arc.slash_subcommand("disable", "Disable auto-slowmode server-wide")
async def server_disable(
    ctx: arc.GatewayContext, database: Database = arc.inject()
) -> None:
    guild_id = ctx.guild_id

    if not guild_id:
        await ctx.respond("This command can only be used in a server.")
        return

    await database.get_guild_config(guild_id)
    await database.update_guild_config(guild_id, is_enabled=0)

    channels = await ctx.client.app.rest.fetch_guild_channels(guild_id)
    for channel in channels:
        text_channel = channel if isinstance(channel, hikari.GuildTextChannel) else None
        if text_channel:
            await database.get_channel_config(text_channel.id, guild_id)
            await database.update_channel_config(text_channel.id, is_enabled=0)

    await ctx.respond("Auto-slowmode has been disabled server-wide")
    logger.info(
        f"Auto-slowmode disabled server-wide for guild {guild_id} by user {ctx.author.id}"
    )


@server_group.include
@arc.slash_subcommand(
    "threshold", "Set the default message rate threshold for the server"
)
async def server_threshold(
    ctx: arc.GatewayContext,
    threshold: arc.Option[
        int,
        arc.IntParams(
            "The message rate threshold (messages per minute)", min=1, max=1000
        ),
    ],
    database: Database = arc.inject(),
) -> None:
    guild_id = ctx.guild_id

    if not guild_id:
        await ctx.respond("This command can only be used in a server.")
        return

    await database.get_guild_config(guild_id)
    await database.update_guild_config(guild_id, default_threshold=threshold)

    await ctx.respond(
        f"Default auto-slowmode threshold for this server has been set to {threshold} messages per minute"
    )
    logger.info(
        f"Auto-slowmode default threshold set to {threshold} for guild {guild_id} by user {ctx.author.id}"
    )


@auto_slowmode.include
@arc.slash_subcommand("stats", "View current activity and slowmode statistics")
async def stats(
    ctx: arc.GatewayContext,
    channel: arc.Option[
        hikari.TextableGuildChannel | None,
        arc.ChannelParams("The channel to view statistics for"),
    ] = None,
    database: Database = arc.inject(),
) -> None:
    if not channel:
        channel_in = ctx.channel
    else:
        channel_in = channel

    guild_id = ctx.guild_id

    if not guild_id:
        await ctx.respond("This command can only be used in a server.")
        return

    guild_config = await database.get_guild_config(guild_id)
    channel_config = await database.get_channel_config(channel_in.id, guild_id)

    channel_enabled = channel_config["is_enabled"] == 1
    guild_enabled = guild_config["is_enabled"] == 1

    if not channel_enabled:
        embed = hikari.Embed(
            title="Auto Slowmode Statistics",
            description=f"Auto Slowmode is not enabled for {channel_in.mention} hence no messages were tracked.",
            color=0xFF0000,
        )
        await ctx.respond(embed=embed)
        return

    if channel_enabled and not guild_enabled:
        notice = "⚠️ **Note:** Auto-slowmode is enabled for this channel but disabled server-wide."
    else:
        notice = ""

    message_count_1m = await database.get_channel_activity(channel_in.id, 60)
    message_count_5m = await database.get_channel_activity(channel_in.id, 300)
    message_count_15m = await database.get_channel_activity(channel_in.id, 900)

    channel_slowmode = await ctx.client.app.rest.fetch_channel(channel_in.id)

    current_slowmode = 0
    if isinstance(channel_slowmode, hikari.GuildTextChannel):
        if channel_slowmode.rate_limit_per_user is not None:
            if isinstance(channel_slowmode.rate_limit_per_user, datetime.timedelta):
                current_slowmode = int(
                    channel_slowmode.rate_limit_per_user.total_seconds()
                )
            else:
                current_slowmode = int(channel_slowmode.rate_limit_per_user)

    threshold = channel_config["threshold"] or guild_config["default_threshold"]

    current_rate = calculate_message_rate(channel_in.id)

    rate_5m = message_count_5m / 5 if message_count_5m > 0 else 0
    rate_15m = message_count_15m / 15 if message_count_15m > 0 else 0

    response = (
        f"**Auto-Slowmode Statistics for {channel_in.mention}**\n\n"
        f"**Status:** {'Enabled' if channel_enabled and guild_enabled else 'Partially Enabled'}\n"
        f"**Message Rate Threshold:** {threshold} messages per minute\n\n"
        f"**Current Activity:**\n"
        f"• Current rate: {current_rate:.1f} messages per minute\n"
        f"• Last minute: {message_count_1m} messages ({message_count_1m} msg/min)\n"
        f"• Last 5 minutes: {message_count_5m} messages ({rate_5m:.1f} msg/min avg)\n"
        f"• Last 15 minutes: {message_count_15m} messages ({rate_15m:.1f} msg/min avg)\n\n"
        f"**Current Slowmode:** {current_slowmode} seconds"
    )

    if notice:
        response += f"\n\n{notice}"

    embed = hikari.Embed(
        title="Auto Slowmode Statistics",
        description=response,
        color=0x00FF00 if channel_enabled and guild_enabled else 0xFFA500,
    )

    await ctx.respond(embed=embed)


@arc.loader
def loader(client: arc.GatewayClient) -> None:
    client.add_plugin(plugin)


@arc.unloader
def unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(plugin)
