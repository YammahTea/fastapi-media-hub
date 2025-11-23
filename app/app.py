from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends

from app.db import Post, create_db_and_tables, get_async_session, User
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select

from app.images import imageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
import os, tempfile, uuid, shutil

from app.users import auth_backend, current_active_user, fastapi_users
from app.schemas import PostCreate, PostResponse, UserCreate, UserRead, UserUpdate

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables() #creates the db
    yield


app = FastAPI(lifespan=lifespan) #it will run lifespan function as soon as the application gets started


"""Connect endpoints from fastapi_users"""
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix='/auth/jwt', tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])


"""Make new post"""
@app.post("/upload")
async def upload_file(
        file: UploadFile = File(...), #To receive a file object to this endpoint
        caption: str = Form(""),
        session: AsyncSession = Depends(get_async_session),
        user: User = Depends(current_active_user)
):

    temp_file_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)


        upload_result = imageKit.upload_file(

            file = open(temp_file_path, "rb"),
            file_name=file.filename,
            options=UploadFileRequestOptions(
                use_unique_file_name=True,
                tags=["backend-upload"]
            )
        )

        if upload_result.response_metadata.http_status_code == 200:

            post = Post(
                user_id= user.id,
                caption = caption,
                url= upload_result.url,
                file_type = "Video" if file.content_type.startswith("video/") else "Image",
                file_name = upload_result.name
            )

            session.add(post)
            await session.commit()
            await session.refresh(post)
            return post

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        file.file.close()


"""Get all posts"""
@app.get("/fyp")
async def get_fyp(
        session: AsyncSession = Depends(get_async_session),
        user: User = Depends(current_active_user)

):
    result = await session.execute(select(Post).order_by(Post.created_at.desc()))
    posts = [row[0] for row in result.all()]

    posts_data = []
    for post in posts:
        posts_data.append({

            "id": str(post.id),
            "user_id": str(post.user_id),
            "caption": post.caption,
            "url": post.url,
            "file_type": post.file_type,
            "file_name": post.file_name,
            "created_at": post.created_at.isoformat(), #YY-MM-DD
            "is_owner": post.user_id == user.id
        })

    return {"posts": posts_data}


"""Delete post by id"""
@app.delete("/posts/{post_id}")
async def delete_post(post_id: str,  session: AsyncSession = Depends(get_async_session), user: User = Depends(current_active_user)):

    try:
        post_uuid = uuid.UUID(post_id) # convert the str to object to use it in the where statement

        result = await session.execute(select(Post).where(Post.id == post_uuid))
        post = result.scalars().first() # just not to deal with object returned

        if not post:
            raise HTTPException(status_code= 404, detail="Post not found")

        if post.user_id == user.id:
            raise HTTPException(status_code=403, detail="You don't have permission to delete this post")

        await session.delete(post)
        await session.commit()

        return {"Success": True, "message": "Post has been deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))