from fastapi import FastAPI

app = FastAPI()

@app.get("/hello-world")
def hello_world():
    return {"message": "hello!"}
    #Why do we return a dict? because when we create APIs, we deal with something called JSON (Javascript Object Notation)
