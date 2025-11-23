from collections.abc import AsyncGenerator
import uuid

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
from fastapi_users.db import SQLAlchemyUserDatabase, SQLAlchemyBaseUserTableUUID
from fastapi import Depends

"""Setup the database"""

DATABASE_URL = "sqlite+aiosqlite:///./test.db"  # This will connect to a local db file on your computer
# If you want to connect to a production database, you will have to change the URL for the database of your choosing

class Base(DeclarativeBase):
    # You have to inherit the class Base as it's not allowed to inherit DeclarativeBase directly below
    pass

"""USER database"""
class User(SQLAlchemyBaseUserTableUUID, Base):
    posts = relationship("Post", back_populates="user")  # to make a link between Post database

"""POSTS database"""
class Post(Base):
    # so this part tells it that we are making a data model
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    caption = Column(Text)
    url = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="posts") # to make a link between user database

"""Creating the database"""

engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

"""Access the database and read and write from it"""
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)