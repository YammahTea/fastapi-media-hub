import asyncio
import os
import shutil
import tempfile
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db import Post, create_db_and_tables, get_async_session, User
from app.images import imageKit
from app.users import auth_backend, current_active_user, fastapi_users
from app.schemas import PostCreate, PostResponse, UserCreate, UserRead, UserUpdate
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()  # creates the db
    yield


app = FastAPI(lifespan=lifespan)  # it will run lifespan function as soon as the application gets started

"""Connect endpoints from fastapi_users"""
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix='/auth/jwt', tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])


# --- Helper for blocking I/O ---
def upload_to_imagekit_sync(file_obj, filename):
    """Wrapper to run synchronous ImageKit code in a thread."""
    return imageKit.upload_file(
        file=file_obj,
        file_name=filename,
        options=UploadFileRequestOptions(
            use_unique_file_name=True,
            tags=["backend-upload"]
        )
    )


"""Make new post"""


@app.post("/upload")
async def upload_file(
        file: UploadFile = File(...),  # To receive a file object to this endpoint
        caption: str = Form(""),
        session: AsyncSession = Depends(get_async_session),
        user: User = Depends(current_active_user)
):
    temp_file_path = None

    try:
        # ADDED: Handling file I/O in a thread to prevent blocking the async event loop
        suffix = os.path.splitext(file.filename)[1]

        def save_temp_file():
            # Create a temp file to store upload locally before sending to cloud
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            shutil.copyfileobj(file.file, tmp)
            tmp.close()
            return tmp.name

        # Run the blocking save function in a separate thread
        temp_file_path = await asyncio.to_thread(save_temp_file)

        # ADDED: Run ImageKit upload in a separate thread
        with open(temp_file_path, "rb") as f:
            upload_result = await asyncio.to_thread(
                upload_to_imagekit_sync, f, file.filename
            )

        if upload_result.response_metadata.http_status_code == 200:
            post = Post(
                user_id=user.id,
                caption=caption,
                url=upload_result.url,
                file_type="Video" if file.content_type.startswith("video/") else "Image",
                file_name=upload_result.name
            )

            session.add(post)
            await session.commit()
            await session.refresh(post)

            # Note: If you need to return the user's email here, you must eager load the user relationship
            # For now, we return the raw post object as requested
            return post

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up local temp file
        if temp_file_path and os.path.exists(temp_file_path):
            await asyncio.to_thread(os.unlink, temp_file_path)
        await file.close()


"""Get all posts"""


@app.get("/fyp")
async def get_fyp(
        session: AsyncSession = Depends(get_async_session),
        user: User = Depends(current_active_user)
):
    # CHANGED: Optimized query. We use `joinedload` to fetch the User info
    # alongside the Post in one single SQL query, preventing the "N+1" problem.
    query = (
        select(Post)
        .options(joinedload(Post.user))
        .order_by(Post.created_at.desc())
    )

    result = await session.execute(query)
    posts = result.scalars().all()

    posts_data = []
    for post in posts:
        posts_data.append({
            "id": str(post.id),
            "user_id": str(post.user_id),
            "caption": post.caption,
            "url": post.url,
            "file_type": post.file_type,
            "file_name": post.file_name,
            "created_at": post.created_at.isoformat(),  # YY-MM-DD
            "is_owner": post.user_id == user.id,
            # CHANGED: We can now access post.user.email directly because of joinedload
            "email": post.user.email if post.user else "Unknown"
        })

    return {"posts": posts_data}


"""Delete post by id"""

@app.delete("/posts/{post_id}")
async def delete_post(
        post_id: uuid.UUID,  # CHANGED: Type hint as uuid.UUID so FastAPI validates it automatically
        session: AsyncSession = Depends(get_async_session),
        user: User = Depends(current_active_user)
):
    try:
        # No need to manually convert string to UUID, FastAPI did it above
        result = await session.execute(select(Post).where(post_id == Post.id))
        post = result.scalars().first()  # just not to deal with object returned

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        # Only allow the owner to delete their post
        if post.user_id != user.id:
            raise HTTPException(status_code=403, detail="You don't have permission to delete this post")

        await session.delete(post)
        await session.commit()

        return {"Success": True, "message": "Post has been deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))