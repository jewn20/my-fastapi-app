from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
import os
import uvicorn

app = FastAPI()


# Force PORT to 8080 since Railway is setting it
port = int(os.getenv("PORT", 8080))

print(f"🚀 Running on port: {port}")  # Debugging output

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

# Set up templates and static files
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

@app.post("/sync-sales")
async def sync_sales(request: Request):
    data = await request.json()

    conn = sqlite3.connect("sales.db")
    cursor = conn.cursor()

    for sale in data["sales"]:
        cursor.execute("""
            INSERT INTO sales (id, date, cashier, product, amount, synced) 
            VALUES (?, ?, ?, ?, ?, 1) 
            ON CONFLICT(id) DO UPDATE SET synced = 1
        """, (sale["id"], sale["date"], sale["cashier"], sale["product"], sale["amount"]))

    conn.commit()
    conn.close()

    return {"message": "Sales synced successfully"}

# Function to get database connection - DEFINE IT HERE
def get_db():
    conn = sqlite3.connect("sales.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/sales/daily")
async def daily_sales_page(request: Request):
    today = datetime.now().strftime("%Y-%m-%d")  # Get current date in YYYY-MM-DD format
    return templates.TemplateResponse("daily_sales.html", {"request": request, "today": today})

@app.get("/sales/data")
async def get_sales_data(
    report_type: str,
    date: str,
    db=Depends(get_db),  # Now get_db is defined before being used
    page: int = 1,
    page_size: int = 12
):
    conn = db
    cursor = conn.cursor()

    valid_report_types = ["DAILY", "MONTHLY", "YEARLY"]
    if report_type not in valid_report_types:
        raise HTTPException(status_code=400, detail="Invalid report type")

    try:
        if report_type == "DAILY":
            datetime.strptime(date, "%Y-%m-%d")
            query = "SELECT date, cashier, product, amount FROM sales WHERE date = ?"
            params = (date,)
        elif report_type == "MONTHLY":
            datetime.strptime(date[:7] + "-01", "%Y-%m-%d")
            query = "SELECT date, cashier, product, amount FROM sales WHERE strftime('%Y-%m', date) = ?"
            params = (date[:7],)
        elif report_type == "YEARLY":
            datetime.strptime(date[:4] + "-01-01", "%Y-%m-%d")
            query = "SELECT date, cashier, product, amount FROM sales WHERE strftime('%Y', date) = ?"
            params = (date[:4],)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    # Calculate total sales BEFORE pagination
    total_sales_query = "SELECT SUM(amount) FROM (" + query + ")" # Get the sum before pagination
    cursor.execute(total_sales_query, params)
    total_sales = cursor.fetchone()[0] or 0  # Use 0 if the result is None

    # Get total count before pagination
    count_query = "SELECT COUNT(*) FROM (" + query + ")"
    cursor.execute(count_query, params)
    total_items = cursor.fetchone()[0]

    # Paginate the data
    offset = (page - 1) * page_size
    query += " LIMIT ? OFFSET ?"
    params = params + (page_size, offset) # Add pagination params
    cursor.execute(query, params)

    sales = cursor.fetchall()

    conn.close()

    total_pages = (total_items + page_size - 1) // page_size

    return {
        "report_type": report_type,
        "date": date,
        "sales": [dict(row) for row in sales],
        "total_sales": total_sales,
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages
    }