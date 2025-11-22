from fastapi import FastAPI, HTTPException
from app.schemas import CreatePost

app = FastAPI()

text_posts = {
    1: {
        "title": "My first reel",
        "description": "I love this app! It's so much faster than the other ones."
    },
    2: {
        "title": "Japan Trip 2026",
        "description": "Can't wait to visit Tokyo and eat ramen in Shibuya!"
    },
    3: {
        "title": "Coding Late Night",
        "description": "Debugging FastAPI at 2 AM. The grind never stops. ☕"
    },
    4: {
        "title": "Gym Progress",
        "description": "Hit a new PR on deadlifts today. Feeling strong."
    },
    5: {
        "title": "Python vs Go",
        "description": "Still deciding which one to use for my backend. Thoughts?"
    },
    6: {
        "title": "Weekend Vibes",
        "description": "Just relaxing and watching movies."
    }
}
"""
GET operations:
posts
post by id
"""
@app.get("/posts")
def get_posts(limit: int = None):
    if limit and (limit < len(text_posts)):
        return list(text_posts.values())[:limit]
    return text_posts

@app.get("/posts/{id}")
def get_post_with_id(id: int):
    if id not in text_posts.keys():
        raise HTTPException(status_code=404, detail="Post not found. The link may be broken, or the profile may have been removed.")

    return text_posts.get(id)

"""
POST operations:
create_post
"""

@app.post("/posts")
def create_post(post: CreatePost): #FastApi will also do the data validation in "post" object, it will raise an error otherwise
    new_post = {"title": post.title, "description": post.description}
    text_posts[max(text_posts.keys())  + 1] = new_post
    return new_post


