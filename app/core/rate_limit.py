from slowapi import Limiter
from slowapi.util import get_remote_address

# Create a global limiter instance with default in-memory storage
limiter = Limiter(key_func=get_remote_address)
