import asyncio
import functools

class ConnectionLimiter:
    def __init__(self, max_connections: int):
        self.semaphore = asyncio.Semaphore(max_connections)
    
    def limit_connections(self, func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            async with self.semaphore:
                return await func(*args, **kwargs)
        return wrapper
