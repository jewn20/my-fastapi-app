from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from pathlib import Path
import os
import uvicorn
import aiosqlite
import logging

app = FastAPI()

# Set up templates and static files
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

logging.basicConfig(level=logging.INFO)
port = int(os.getenv("PORT", 8080))
print(f"🚀 Running on port: {port}")

async def get_db():
    async with aiosqlite.connect("sales.db") as db:
        db.row_factory = aiosqlite.Row
        yield db

@app.on_event("startup")
async def startup_event():
    async with aiosqlite.connect("sales.db") as db:
        await db.execute("SELECT 1")
        await db.commit()
        logging.info("Database connection test successful.")

@app.post("/sync-sales")
async def sync_sales(request: Request):
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
        logging.info(f"Synced {len(data['sales'])} sales.")
    return {"message": "Sales synced successfully"}

@app.get("/")
async def daily_sales_page(request: Request):
    return templates.TemplateResponse("daily_sales.html", {"request": request, "today": datetime.now().strftime("%Y-%m-%d")})

@app.get("/data")
async def get_sales_data(report_type: str, date: str, page: int = 1, page_size: int = 12, db: aiosqlite.Connection = Depends(get_db)):
    valid_report_types = {"DAILY": "%Y-%m-%d", "MONTHLY": "%Y-%m", "YEARLY": "%Y"}
    if report_type not in valid_report_types:
        raise HTTPException(status_code=400, detail="Invalid report type")

    try:
        # Use the correct length of the date
        if report_type == "MONTHLY":
            date = date[:7]  # Keep only YYYY-MM
        elif report_type == "YEARLY":
            date = date[:4]  # Keep only YYYY
        datetime.strptime(date, valid_report_types[report_type])
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    query = "SELECT date, cashier, product, amount FROM sales WHERE strftime(?, date) = ?"
    params = (valid_report_types[report_type], date)
    offset = (page - 1) * page_size

    async with db.execute(f"""
        WITH sales_filtered AS (
            {query}
        )
        SELECT *, (SELECT SUM(amount) FROM sales_filtered) AS total_sales,
                 (SELECT COUNT(*) FROM sales_filtered) AS total_items
        FROM sales_filtered LIMIT ? OFFSET ?
    """, params + (page_size, offset)) as cursor:
        sales = await cursor.fetchall()

    if not sales:
        return {"sales": [], "total_sales": 0, "total_items": 0, "total_pages": 0}

    total_sales, total_items = sales[0]["total_sales"], sales[0]["total_items"]
    return {
        "report_type": report_type,
        "date": date,
        "sales": [dict(row) for row in sales],
        "total_sales": total_sales,
        "total_items": total_items,
        "total_pages": (total_items + page_size - 1) // page_size,
        "page": page,
        "page_size": page_size
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)