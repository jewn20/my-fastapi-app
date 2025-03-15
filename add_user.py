import aiosqlite
import bcrypt
import asyncio

async def add_admin():
    db = await aiosqlite.connect("sales.db")
    hashed_pw = bcrypt.hashpw("@Rebele20".encode(), bcrypt.gensalt()).decode()
    await db.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", ("jewn", hashed_pw, "admin"))
    await db.commit()
    await db.close()
    print("Admin user added!")

asyncio.run(add_admin())
