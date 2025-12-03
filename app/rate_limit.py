from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

# create the limiter instance
# uses IP address to track requests
limiter = Limiter(key_func=get_remote_address)

# default rate limit string
default_limit = f"{settings.rate_limit_per_minute}/minute"
