from typing import (
    Any,
    Dict,
    Literal,
    Optional,
    Awaitable,
    List,
    Tuple,
    Union,
)

try:
    import asyncpg  # type: ignore

    _HAS_ASYNCPG = True
except ImportError:
    _HAS_ASYNCPG = False


class StorageMixin:
    def set(self, k: str, val: Any) -> None:
        raise NotImplementedError()

    def get(self, k: str, default: Optional[Any] = None) -> Any:
        raise NotImplementedError()

    def delete(self, k: str, default: Optional[Any] = None) -> Any:
        raise NotImplementedError()

    def items(self):
        raise NotImplementedError()


class AsyncStorageMixin:
    async def set(self, k: str, val: Any) -> None:
        raise NotImplementedError()

    async def get(self, k: str, default: Optional[Any] = None) -> Any:
        raise NotImplementedError()

    async def delete(self, k: str, default: Optional[Any] = None) -> Any:
        raise NotImplementedError()

    async def items(self):
        raise NotImplementedError()


class SessionStorageMixin:
    def close(self) -> None:
        raise NotImplementedError()


class AsyncSessionStorageMixin:
    async def close(self) -> None:
        raise NotImplementedError()


class InMemoryStorage(StorageMixin):
    def __init__(self) -> None:
        self._items: Dict[str, Any] = {}

    def items(self) -> Dict[str, Any]:
        return self._items

    def set(self, k: str, val: Any) -> None:
        self._items[k] = val

    def get(self, k: str, default: Optional[Any] = None) -> Any:
        return self._items.get(k, default=default)

    def delete(self, k: str, default: Optional[Any] = None) -> Any:
        return self._items.pop(k, default=default)

    def __repr__(self) -> str:
        return "<{}>".format(repr(self._items))


class MockAsyncStorage(AsyncSessionStorageMixin, AsyncStorageMixin):
    def __init__(self) -> None:
        self._items: Dict[Any, Any] = {}

    async def get(self, k: str, default: Optional[Any] = None) -> Any:
        return self._items.get(k, default)

    async def set(self, k: str, val: Any) -> None:
        self._items[k] = val

    async def delete(self, k: str, default: Optional[Any] = None) -> Any:
        return self._items.pop(k, default=default)

    async def close(self) -> None:
        pass

    async def items(self):
        return self._items.items()


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


class DatabaseMixin:
    def __await__(self):
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError

    async def get_guild(self, guild_id: int) -> GuildChannels:
        raise NotImplementedError

    async def get_channel(
        self, channel_id: int, channel_type: int
    ) -> Optional[Channel]:
        raise NotImplementedError

    async def add_channel(self, channel: Channel) -> None:
        raise NotImplementedError

    async def update_channel(self, channel: Channel) -> None:
        raise NotImplementedError

    async def get_channels(self, channel_type: int) -> List[Channel]:
        raise NotImplementedError

    async def remove_channel(self, channel: Channel) -> None:
        raise NotImplementedError


if _HAS_ASYNCPG:

    class PostgresStorage(DatabaseMixin):
        def __init__(self, dsn: str):

            self._dsn: str = dsn
            self._pool: Optional[asyncpg.Pool] = None

        def _check_pool(self):
            if self._pool is None:
                raise RuntimeError("Object is not awaited")

        async def __await__impl(self) -> "PostgresStorage":
            if self._pool is not None:
                return self

            self._pool = await asyncpg.create_pool(self._dsn)
            return self

        def __await__(self) -> Awaitable["PostgresStorage"]:
            return self.__await__impl().__await__()

        async def close(self) -> None:
            await self._pool.close()

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
