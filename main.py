from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from pathlib import Path
import aiosqlite
import bcrypt
import os
import uvicorn

app = FastAPI()

# Set up templates and static files
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Authentication
SECURITY = HTTPBasic()

async def get_db():
    async with aiosqlite.connect("sales.db") as db:
        db.row_factory = aiosqlite.Row
        yield db

async def verify_user(credentials: HTTPBasicCredentials = Depends(SECURITY), db=Depends(get_db)):
    async with db.execute("SELECT username, password_hash, role FROM users WHERE username = ?", (credentials.username,)) as cursor:
        user = await cursor.fetchone()
        if not user or not bcrypt.checkpw(credentials.password.encode(), user["password_hash"].encode()):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Basic"},
            )
    return {"username": user["username"], "role": user["role"]}

@app.on_event("startup")
async def startup_event():
    async with aiosqlite.connect("sales.db") as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.commit()

@app.post("/sync-sales")
async def sync_sales(request: Request, user: dict = Depends(verify_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin users can sync sales.")
    
    data = await request.json()
    async with aiosqlite.connect("sales.db") as db:
        for sale in data["sales"]:
            await db.execute(
                """
                INSERT INTO sales (id, date, cashier, product, amount, synced)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(id) DO UPDATE SET date=?, cashier=?, product=?, amount=?, synced=1
                """,
                (sale["id"], sale["date"], sale["cashier"], sale["product"], sale["amount"],
                 sale["date"], sale["cashier"], sale["product"], sale["amount"])
            )
        await db.commit()
    return {"message": "Sales synced successfully"}

@app.get("/")
async def daily_sales_page(request: Request, user: dict = Depends(verify_user)):
    return templates.TemplateResponse("daily_sales.html", {"request": request, "today": datetime.now().strftime("%Y-%m-%d"), "user": user})

@app.post("/add-user")
async def add_user(username: str, password: str, role: str, db=Depends(get_db), user: dict = Depends(verify_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin users can add users.")

    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        async with db.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", (username, hashed_pw, role)):
            await db.commit()
    except aiosqlite.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")

    return {"message": "User added successfully"}
