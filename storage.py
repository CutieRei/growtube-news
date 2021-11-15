
try:
    import replit
    _HAS_REPLIT = True
except ImportError:
    _HAS_REPLIT = False
    
from typing import Any, Dict, Optional, Awaitable, List

try:
    import asyncpg
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

if _HAS_REPLIT:
    class ReplitStorage(SessionStorageMixin, StorageMixin):
    
        def __init__(self, db_url: Optional[str] = None) -> None:
            
            self._db: replit.Database = replit.db or replit.Database(db_url or replit.database.db_url)
    
        def get(self, k: str, default: Optional[Any] = None) -> Any:
            return self._db.get(k, default=default)
        
        def set(self, k: str, val: Any) -> None:
            return self._db.set(k, val)
        
        def delete(self, k: str, default: Optional[Any] = None) -> Any:
    
            class _None:
                pass
    
            item = self.get(k, default=_None)
            if item is _None:
                return default
    
            del self._db[k]
            return item
        
        def close(self) -> None:
            self._db.close()
        
        def items(self):
            return self._db.items()
    
    class AsyncReplitStorage(AsyncSessionStorageMixin, AsyncStorageMixin):
    
        def __init__(self, db_url: Optional[str] = None) -> None:
            
            self._db: replit.AsyncDatabase = replit.AsyncDatabase(db_url or replit.database.db_url)
        
        async def get(self, k: str, default: Optional[Any] = None) -> Any:
            try:
                return await self._db.get(k)
            except KeyError:
                return default
        
        async def set(self, k: str, val: Any) -> None:
            await self._db.set(k, val)
        
        async def delete(self, k: str, default: Optional[Any] = None) -> Any:
            
            class _None:
                pass
    
            item = await self.get(k, default=_None)
    
            if item is _None:
                return default
    
            await self._db.delete(k)
            return item
        
        async def close(self) -> None:
            await self._db.sess.close()
        
        async def items(self):
            return await self._db.items()

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
    
    def __init__(self, channel, webhook, token) -> None:
        
        self._channel = channel
        self._webhook = webhook
        self._token = token
    
    @property
    def channel(self):
        return self._channel
    
    @property
    def webhook(self):
        return self._webhook
    
    @property
    def token(self):
        return self._token
    
if _HAS_ASYNCPG:
    class GuildChannels:
        
        def __init__(self, records: List[asyncpg.Record]) -> None:
            
            self._items = {
            i["type"]: Channel(i["channel"], i["webhook"], i["token"]) for i in records
                }
        
        def __getitem__(self, k: int):
            return self._items.get(k)
            
    class PostgresStorage:
        
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
        
        async def get_guild(self, guild_id: int) -> Any:
            records = await self._pool.fetch("SELECT * FROM channels WHERE guild = $1", guild_id)
            return GuildChannels(records)
        
        async def add_channel(self, guild_id: int, channel_type: int, channel: Channel) -> None:
            await self._pool.execute("""
                INSERT INTO channels (guild, type, channel, webhook, token) SELECT $1,$2,$3,$4,$5 WHERE NOT EXISTS (SELECT 1 FROM channels WHERE guild = $1 AND type = $2)
                """, guild_id, channel_type, channel.channel, channel.webhook, channel.token)
        
        async def update_channel(self, guild_id: int, channel_type: int, channel: Channel) -> None:
            await self._pool.execute("""
                UPDATE channels SET channel = $1, webhook = $2, token = $3 WHERE guild = $4 AND type = $5
                """, channel.channel, channel.webhook, channel.token, guild_id, channel_type)
    