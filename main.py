from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Hello from Railway! Your FastAPI is live!"}

@app.get("/hello")
def say_hello():
    return {"message": "This is a new route!"}
