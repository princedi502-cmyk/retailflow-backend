from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.storage import MemoryStorage
import os

# Use memory storage as fallback when Redis is not available
storage = MemoryStorage()

# Create a global limiter instance with memory storage
limiter = Limiter(key_func=get_remote_address, storage=storage)
