import aiosqlite
import bcrypt
import asyncio

async def add_admin():
    try:
        async with aiosqlite.connect("sales.db") as db:
            hashed_pw = bcrypt.hashpw("@Rebele20".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            await db.execute("INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?)", ("jewn", hashed_pw, "admin"))
            await db.commit()
            print("Admin user added!")
    except Exception as e:
        print(f"Error adding admin user: {e}")

asyncio.run(add_admin())