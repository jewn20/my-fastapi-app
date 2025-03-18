from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import aiosqlite
import os
from datetime import datetime
from pathlib import Path
import bcrypt
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()
# Set up templates and static files
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Hash password
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

# Verify Password
def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

# Get the database
async def get_db():
    async with aiosqlite.connect("sales.db") as db:
        db.row_factory = aiosqlite.Row
        yield db

# Home Page
@app.get("/", response_class=HTMLResponse)
async def daily_sales_page(request: Request):
    return templates.TemplateResponse("daily_sales.html", {"request": request, "today": datetime.now().strftime("%Y-%m-%d")})

# Login page
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# login
@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    async with aiosqlite.connect("sales.db") as db:
        async with db.execute("SELECT id, username, hashed_password FROM users WHERE username = ?", (username,)) as cursor:
            user = await cursor.fetchone()
        if user is None:
            return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})
        user_id, db_username, hashed_password = user[0], user[1], user[2]
        if not verify_password(password, hashed_password):
            return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})
    response = RedirectResponse("/", status_code=302) # after login redirect back to home.
    response.set_cookie(key="user_id", value=str(user_id), httponly=True, secure=False)
    return response

# Main Function
port = int(os.getenv("PORT", 8080))
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)