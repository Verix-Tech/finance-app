from auth.auth import get_current_active_user, User
from fastapi import Depends

# Re-export the authentication dependency
get_current_user = get_current_active_user 