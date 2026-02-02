"""
Create SQLite database and populate with sample complaints for testing
Run this after switching to SQLite in .env
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.db.base import Base
from app.db.models import Complaint
from datetime import datetime, timedelta
import random

DATABASE_URL = "sqlite+aiosqlite:///./app.db"

async def init_db():
    """Create all tables"""
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        # Drop all tables (fresh start)
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    print("[SUCCESS] Database tables created")
    
    # Create session for adding data
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    # Sample data
    sample_complaints = [
        {
            "flat_number": "A-101",
            "category": "Plumbing",
            "priority": "high",
            "description": "Water leakage in bathroom. Urgent repair needed as water is flooding the floor.",
            "status": "pending",
            "source": "voice"
        },
        {
            "flat_number": "B-205",
            "category": "Electrical",
            "priority": "high",
            "description": "Power outage in bedroom. Circuit breaker keeps tripping.",
            "status": "in-progress",
            "source": "voice"
        },
        {
            "flat_number": "C-304",
            "category": "Maintenance",
            "priority": "medium",
            "description": "Air conditioning not cooling properly. Temperature control not working.",
            "status": "pending",
            "source": "voice"
        },
        {
            "flat_number": "A-102",
            "category": "Noise",
            "priority": "low",
            "description": "Neighbors making loud noise late at night. Disturbing sleep.",
            "status": "resolved",
            "source": "voice"
        },
        {
            "flat_number": "D-401",
            "category": "Plumbing",
            "priority": "medium",
            "description": "Kitchen sink drain is clogged. Water not draining properly.",
            "status": "in-progress",
            "source": "voice"
        },
        {
            "flat_number": "B-203",
            "category": "Security",
            "priority": "high",
            "description": "Main entrance lock is broken. Security concern for all residents.",
            "status": "pending",
            "source": "voice"
        },
        {
            "flat_number": "C-301",
            "category": "Pest Control",
            "priority": "medium",
            "description": "Cockroaches in kitchen area. Require immediate pest control service.",
            "status": "pending",
            "source": "voice"
        },
        {
            "flat_number": "A-105",
            "category": "Electrical",
            "priority": "low",
            "description": "Hallway light flickering intermittently. Not urgent but needs fixing.",
            "status": "resolved",
            "source": "voice"
        },
        {
            "flat_number": "D-402",
            "category": "Maintenance",
            "priority": "high",
            "description": "Elevator stuck on 4th floor. People are trapped inside. Emergency!",
            "status": "in-progress",
            "source": "voice"
        },
        {
            "flat_number": "B-201",
            "category": "Parking",
            "priority": "low",
            "description": "Parking spot occupied by unknown vehicle. Need to clear space.",
            "status": "pending",
            "source": "voice"
        },
    ]
    
    async with async_session() as session:
        # Add complaints with varying created_at dates
        for i, complaint_data in enumerate(sample_complaints):
            # Spread complaints across last 7 days
            days_ago = random.randint(0, 6)
            created_at = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
            
            complaint = Complaint(
                **complaint_data,
                created_at=created_at
            )
            session.add(complaint)
        
        await session.commit()
    
    print(f"[SUCCESS] Added {len(sample_complaints)} sample complaints")
    print("\n[READY] Database ready! Restart uvicorn and open http://localhost:5173")

if __name__ == "__main__":
    asyncio.run(init_db())
