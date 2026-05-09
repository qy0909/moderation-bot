import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                dsn=os.getenv("DATABASE_URL"),
                min_size=5,
                max_size=20
            )
            print("Successfully connected to the PostgreSQL pool.")

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            print("Database pool closed.")

# Global instance to be used across the project
db = Database()