from pydantic import BaseModel

class CreatePost(BaseModel):
    title: str
    description: str