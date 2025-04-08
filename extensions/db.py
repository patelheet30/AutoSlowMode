import logging
import os
from pathlib import Path
from typing import List, Optional

import aiosqlite
import arc

logger = logging.getLogger("db")


class Database:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.environ.get(
            "DATABASE_PATH", "data/auto_slowmode.db"
        )

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    async def init(self) -> None:
        self.connection = await aiosqlite.connect(self.db_path)
        self.connection.row_factory = aiosqlite.Row

        await self.connection.execute("""
        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id INTEGER PRIMARY KEY,
            is_enabled INTEGER DEFAULT 1,
            default_threshold INTEGER DEFAULT 10,
            update_interval INTEGER DEFAULT 30
        )
        """)

        await self.connection.execute("""
        CREATE TABLE IF NOT EXISTS channel_config (
            channel_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            is_enabled INTEGER DEFAULT 1,
            threshold INTEGER DEFAULT NULL,
            FOREIGN KEY (guild_id) REFERENCES guild_config(guild_id)
        )
        """)

        await self.connection.execute("""
        CREATE TABLE IF NOT EXISTS message_activity (
            channel_id INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            message_count INTEGER DEFAULT 1,
            PRIMARY KEY (channel_id, timestamp),
            FOREIGN KEY (channel_id) REFERENCES channel_config(channel_id)
        )
        """)

        await self.connection.commit()
        logger.info("Database initialized successfully")

    async def close(self) -> None:
        """Close the database connection."""
        if self.connection:
            await self.connection.close()
            logger.info("Database connection closed")

    async def get_guild_config(self, guild_id: int) -> dict:
        async with self.connection.execute(
            "SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            else:
                await self.connection.execute(
                    "INSERT INTO guild_config (guild_id) VALUES (?)", (guild_id,)
                )
                await self.connection.commit()
                return {
                    "guild_id": guild_id,
                    "is_enabled": 1,
                    "default_threshold": 10,
                    "update_interval": 30,
                }

    async def update_guild_config(self, guild_id: int, **kwargs) -> None:
        set_clause = ", ".join(f"{key} = ?" for key in kwargs.keys())
        values = list(kwargs.values())
        values.append(guild_id)

        await self.connection.execute(
            f"UPDATE guild_config SET {set_clause} WHERE guild_id = ?", values
        )
        await self.connection.commit()

    async def get_channel_config(self, channel_id: int, guild_id: int) -> dict:
        """Get the configuration for a channel."""
        async with self.connection.execute(
            "SELECT * FROM channel_config WHERE channel_id = ?", (channel_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            else:
                await self.connection.execute(
                    "INSERT INTO channel_config (channel_id, guild_id) VALUES (?, ?)",
                    (channel_id, guild_id),
                )
                await self.connection.commit()
                return {
                    "channel_id": channel_id,
                    "guild_id": guild_id,
                    "is_enabled": 1,
                    "threshold": None,
                }

    async def update_channel_config(self, channel_id: int, **kwargs) -> None:
        set_clause = ", ".join(f"{key} = ?" for key in kwargs.keys())
        values = list(kwargs.values())
        values.append(channel_id)

        await self.connection.execute(
            f"UPDATE channel_config SET {set_clause} WHERE channel_id = ?", values
        )
        await self.connection.commit()

    async def get_enabled_channels(self, guild_id: int) -> List[dict]:
        async with self.connection.execute(
            "SELECT * FROM channel_config WHERE guild_id = ? AND is_enabled = 1",
            (guild_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def record_message(self, channel_id: int, timestamp: int) -> None:
        rounded_timestamp = (timestamp // 60) * 60

        await self.connection.execute(
            """
            INSERT INTO message_activity (channel_id, timestamp, message_count)
            VALUES (?, ?, 1)
            ON CONFLICT (channel_id, timestamp) DO UPDATE SET
            message_count = message_count + 1
            """,
            (channel_id, rounded_timestamp),
        )
        await self.connection.commit()

    async def get_channel_activity(self, channel_id: int, time_window: int) -> int:
        import time

        current_time = int(time.time())
        start_time = current_time - time_window

        async with self.connection.execute(
            """
            SELECT SUM(message_count) as total_messages
            FROM message_activity
            WHERE channel_id = ? AND timestamp >= ?
            """,
            (channel_id, start_time),
        ) as cursor:
            row = await cursor.fetchone()
            return (
                row["total_messages"]
                if row and row["total_messages"] is not None
                else 0
            )

    async def get_enabled_guilds(self) -> List[dict]:
        async with self.connection.execute(
            """
            SELECT DISTINCT g.* 
            FROM guild_config g
            LEFT JOIN channel_config c ON g.guild_id = c.guild_id
            WHERE g.is_enabled = 1 
            OR (c.is_enabled = 1)
            """
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def cleanup_old_messages(self, max_age: int = 86400) -> None:
        import time

        current_time = int(time.time())
        cutoff_time = current_time - max_age

        await self.connection.execute(
            "DELETE FROM message_activity WHERE timestamp < ?", (cutoff_time,)
        )
        await self.connection.commit()


db = Database()


@arc.loader
def load(client: arc.GatewayClient) -> None:
    client.set_type_dependency(Database, db)

    @client.add_startup_hook
    async def startup(_: arc.GatewayClient) -> None:
        await db.init()
        logger.info("Database initialized and connected")

    @client.add_shutdown_hook
    async def shutdown(_: arc.GatewayClient) -> None:
        await db.close()
        logger.info("Database connection closed during shutdown")


@arc.unloader
def unload(client: arc.GatewayClient) -> None:
    pass
