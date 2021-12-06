from typing import (
    Literal,
    Optional,
    List,
    Tuple,
    Union,
)
import asyncpg


class Channel:
    def __init__(self, guild, channel_type, channel, webhook, token) -> None:

        self._guild = guild
        self._type = channel_type
        self._channel = channel
        self._webhook = webhook
        self._token = token

    @property
    def guild(self) -> int:
        return self._guild

    @property
    def type(self) -> Union[Literal[0], Literal[1], Literal[3]]:
        return self._type

    @property
    def channel(self) -> int:
        return self._channel

    @property
    def webhook(self) -> int:
        return self._webhook

    @property
    def token(self) -> str:
        return self._token


GuildChannels = Tuple[Optional[Channel], Optional[Channel], Optional[Channel]]


class PostgresStorage:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def get_guild(self, guild_id: int) -> GuildChannels:
        records = await self._pool.fetch(
            "SELECT * FROM channels WHERE guild = $1", guild_id
        )
        channels = {i: None for i in range(3)}
        for record in records:
            channels[record["type"]] = Channel(
                record["guild"],
                record["type"],
                record["channel"],
                record["webhook"],
                record["token"],
            )
        return tuple(channels.values())

    async def get_channel(
        self, channel_id: int, channel_type: int
    ) -> Optional[Channel]:
        record = await self._pool.fetchrow(
            "SELECT * FROM channels WHERE channel = $1 and type = $2",
            channel_id,
            channel_type,
        )
        return (
            Channel(
                record["guild"],
                record["type"],
                record["channel"],
                record["webhook"],
                record["token"],
            )
            if record is not None
            else record
        )

    async def add_channel(self, channel: Channel) -> None:
        await self._pool.execute(
            """
                INSERT INTO channels (guild, type, channel, webhook, token) SELECT $1,$2,$3,$4,$5 WHERE NOT EXISTS (SELECT 1 FROM channels WHERE guild = $1 AND type = $2)
                """,
            channel.guild,
            channel.type,
            channel.channel,
            channel.webhook,
            channel.token,
        )

    async def update_channel(self, channel: Channel) -> None:
        await self._pool.execute(
            """
                UPDATE channels SET channel = $1, webhook = $2, token = $3 WHERE guild = $4 AND type = $5
                """,
            channel.channel,
            channel.webhook,
            channel.token,
            channel.guild,
            channel.type,
        )

    async def get_channels(self, channel_type: int) -> List[Channel]:
        return [
            Channel(i["guild"], i["type"], i["channel"], i["webhook"], i["token"])
            for i in await self._pool.fetch(
                "SELECT * FROM channels WHERE type = $1", channel_type
            )
        ]

    async def remove_channel(self, channel: Channel) -> None:
        await self._pool.execute(
            "DELETE FROM channels WHERE channel = $1 AND type = $2",
            channel.channel,
            channel.type,
        )
