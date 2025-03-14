from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import uvicorn
from pathlib import Path
import aiosqlite

app = FastAPI()

# Set up templates
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

async def get_db():
    async with aiosqlite.connect("test.db") as db:  # Use a test database
        yield db

@app.get("/")
async def read_root(request: Request, db: aiosqlite.Connection = Depends(get_db)):
    async with db.cursor() as cursor:
        await cursor.execute("SELECT 1") # Simple test Query
        result = await cursor.fetchone()
    return templates.TemplateResponse("index.html", {"request": request, "db_result": result})

@app.get("/health")
async def health_check():
    return {"status": "ok"}

port = int(os.getenv("PORT", 8080))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)