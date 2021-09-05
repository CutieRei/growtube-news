import replit
from typing import Any, Dict, Optional


class StorageMixin():

    def set(self, k: str, val: Any) -> None:
        raise NotImplementedError()
    
    def get(self, k: str, default: Optional[Any] = None) -> Any:
        raise NotImplementedError()
    
    def delete(self, k: str, default: Optional[Any] = None) -> Any:
        raise NotImplementedError()
    
    def items(self):
        raise NotImplementedError()

class SessionStorageMixin(StorageMixin):

    def close(self) -> None:
        raise NotImplementedError()

class InMemoryStorage(StorageMixin):

    _items: Dict[str, Any]

    def __init__(self) -> None:
        self._items = {}
    
    def set(self, k: str, val: Any) -> None:
        self._items[k] = val
    
    def get(self, k: str, default: Optional[Any] = None) -> Any:
        return self._items.get(k, default=default)
    
    def delete(self, k: str, default: Optional[Any] = None) -> Any:
        return self._items.pop(k, default=default)
    
    def __repr__(self) -> str:
        return "<{}>".format(repr(self._items))

class ReplitStorage(SessionStorageMixin):
    
    _db: replit.Database

    def __init__(self, db_url: Optional[str] = None) -> None:
        
        self._db = replit.db or replit.Database(db_url or replit.database.db_url)

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

class AsyncReplitStorage(SessionStorageMixin):

    _db: replit.AsyncDatabase

    def __init__(self, db_url: Optional[str] = None) -> None:
        self._db = replit.AsyncDatabase(db_url or replit.database.db_url)
    
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

class MockAsyncReplitStorage(SessionStorageMixin):
    
    _items: Dict[Any, Any]

    def __init__(self, *args) -> None:
        self._items = {}
    
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