import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete
from app.database import AsyncSessionLocal
from app.models.chip import Chip

async def cleanup_chips():
    async with AsyncSessionLocal() as session:
        print("Cleaning up chips...")
        await session.execute(delete(Chip))
        await session.commit()
        print("Chips cleaned up.")

if __name__ == "__main__":
    asyncio.run(cleanup_chips())
