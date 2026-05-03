"""
Migration script: Add user_id columns and new tables (User, Notification).
Run once to update existing database schema.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from config import get_settings

settings = get_settings()


async def migrate():
    engine = create_async_engine(settings.database_url, echo=True)

    async with engine.begin() as conn:
        # 1. Create User table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "user" (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'user',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        print("✅ Created 'user' table")

        # 2. Add user_id to traveler
        await conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='traveler' AND column_name='user_id'
                ) THEN
                    ALTER TABLE traveler ADD COLUMN user_id INTEGER UNIQUE REFERENCES "user"(id);
                END IF;
            END $$;
        """))
        print("✅ Added user_id to 'traveler' table")

        # 3. Add user_id to sender
        await conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='sender' AND column_name='user_id'
                ) THEN
                    ALTER TABLE sender ADD COLUMN user_id INTEGER UNIQUE REFERENCES "user"(id);
                END IF;
            END $$;
        """))
        print("✅ Added user_id to 'sender' table")

        # 4. Create Notification table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS notification (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES "user"(id),
                title VARCHAR(200) NOT NULL,
                message TEXT NOT NULL,
                notification_type VARCHAR(50) NOT NULL DEFAULT 'info',
                is_read BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        print("✅ Created 'notification' table")

    await engine.dispose()
    print("\n🎉 Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate())
