from pydantic import BaseModel, ConfigDict
from fastapi_users import schemas
import uuid
from datetime import datetime

# --- Post Schemas ---
class PostBase(BaseModel):
    caption: str

class PostCreate(PostBase):
    pass

class PostResponse(PostBase):
    id: uuid.UUID
    user_id: uuid.UUID
    url: str
    file_type: str
    file_name: str
    created_at: datetime
    email: str | None = None

    model_config = ConfigDict(from_attributes=True)

# --- User Schemas ---

class UserRead(schemas.BaseUser[uuid.UUID]):
    pass

class UserCreate(schemas.BaseUserCreate):
    pass

class UserUpdate(schemas.BaseUserUpdate):
    pass