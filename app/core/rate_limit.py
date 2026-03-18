from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.storage import Storage
from typing import Dict
import time
import asyncio

class MemoryStorage(Storage):
    """Simple in-memory storage for rate limiting"""
    def __init__(self):
        self.storage: Dict[str, list] = {}
        self.lock = asyncio.Lock()
    
    async def incr(self, key: str, expiry: int) -> int:
        async with self.lock:
            now = time.time()
            if key not in self.storage:
                self.storage[key] = []
            
            # Remove expired entries
            self.storage[key] = [
                timestamp for timestamp in self.storage[key]
                if now - timestamp < expiry
            ]
            
            # Add current request
            self.storage[key].append(now)
            return len(self.storage[key])
    
    async def get(self, key: str) -> int:
        async with self.lock:
            return len(self.storage.get(key, []))
    
    async def reset(self, key: str) -> None:
        async with self.lock:
            if key in self.storage:
                del self.storage[key]

# Create a global limiter instance with memory storage
limiter = Limiter(key_func=get_remote_address, storage=MemoryStorage())
