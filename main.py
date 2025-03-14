from fastapi import FastAPI
import os
#import uvicorn

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Hello, world!"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

#port = int(os.getenv("PORT", 8080))

#if __name__ == "__main__":
 #   uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)