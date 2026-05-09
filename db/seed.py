import asyncio
from db.database import db
from db.queries import register_user, log_analyzed_message

async def seed_data():
    await db.connect()
    print("Seeding sample data...")

    # Create a sample server setting (Using integers for BIGINT)
    await db.pool.execute("INSERT INTO moderation_settings (guild_id) VALUES (123456789) ON CONFLICT DO NOTHING")

    # Register a dummy user (Using an integer ID)
    await register_user(987654321, "ToxicBuddy46")

    # Add some fake messages
    for i in range(10):
        await log_analyzed_message({
            'message_id': 1000 + i,
            'guild_id': 123456789,
            'user_id': 987654321,
            'channel_id': 555555,
            'sentiment_score': -0.5,
            'toxicity_score': 0.1 * i, 
            'model_name': 'huggingface-distilbert',
            'model_version': 'v1.0'
        })
    
    print("Database seeded successfully with BIGINT schema!")
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(seed_data())