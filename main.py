from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
import aiosqlite
import logging
from datetime import datetime

app = FastAPI()
templates = Jinja2Templates(directory="templates")

DB_PATH = "sales.db"

# Logging setup
logging.basicConfig(level=logging.INFO)


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db

async def init_sales_table():
    async with aiosqlite.connect("sales.db") as db:
        # Check if the 'sales' table exists
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sales'") as cursor:
            table_exists = await cursor.fetchone()

        # If the table does not exist, create it
        if not table_exists:
            await db.execute("""
                CREATE TABLE sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    cashier TEXT NOT NULL,
                    product TEXT NOT NULL,
                    amount REAL NOT NULL,
                    synced INTEGER DEFAULT 0
                );
            """)
            await db.commit()

@app.on_event("startup")
async def startup_event():
    await init_sales_table()


@app.post("/sync_sales")
async def sync_sales(sales: list[dict]):
    async with aiosqlite.connect(DB_PATH) as db:
        for sale in sales:
            await db.execute(
                "INSERT INTO sales (id, date, cashier, product, amount, synced) VALUES (?, ?, ?, ?, ?, 1) "
                "ON CONFLICT(id) DO UPDATE SET synced = 1",
                (sale["id"], sale["date"], sale["cashier"], sale["product"], sale["amount"]),
            )
        await db.commit()
    return {"status": "success", "synced_count": len(sales)}

@app.get("/")
async def sales_report_page(request: Request):
    today = datetime.today().strftime("%Y-%m-%d")  # Format for HTML input field
    return templates.TemplateResponse("daily_sales.html", {"request": request, "today": today})


@app.get("/data")
async def get_sales_data(
    request: Request, report_type: str, date: str, page: int = 1, page_size: int = 10
):
    try:
        logging.info(f"Fetching {report_type} sales for date: {date}")

        # Convert date to expected database format (MM/DD/YYYY)
        try:
            formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%m/%d/%Y")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            offset = (page - 1) * page_size

            query = "SELECT date, cashier, product, amount FROM sales WHERE date = ? LIMIT ? OFFSET ?"
            async with db.execute(query, (formatted_date, page_size, offset)) as cursor:
                sales = await cursor.fetchall()

            # Get total sales amount
            total_query = "SELECT SUM(amount) FROM sales WHERE date = ?"
            async with db.execute(total_query, (formatted_date,)) as total_cursor:
                total_sales = await total_cursor.fetchone()
                total_sales = total_sales[0] if total_sales[0] is not None else 0.00

            # Get total count for pagination
            count_query = "SELECT COUNT(*) FROM sales WHERE date = ?"
            async with db.execute(count_query, (formatted_date,)) as count_cursor:
                total_count = await count_cursor.fetchone()
                total_records = total_count[0] if total_count[0] is not None else 0
                total_pages = (total_records // page_size) + (1 if total_records % page_size else 0)

        return {
            "sales": [{"date": row["date"], "cashier": row["cashier"], "product": row["product"], "amount": row["amount"]} for row in sales],
            "total_sales": total_sales,
            "page": page,
            "total_pages": total_pages,
        }

    except Exception as e:
        logging.error(f"Error fetching sales data: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while fetching the data.")
