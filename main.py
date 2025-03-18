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
