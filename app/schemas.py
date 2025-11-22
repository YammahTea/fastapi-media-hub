from pydantic import BaseModel

class PostCreate(BaseModel):
    title: str
    description: str

class PostResponse(BaseModel):
    title: str
    description: str