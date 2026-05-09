import logging
from db.database import db

# Professional logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DatabaseAgent")

async def register_user(user_id: int, username: str):
    """Ensures a user exists in the system before logging messages."""
    try:
        query = """
            INSERT INTO users (user_id, username)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET username = $2, last_seen = CURRENT_TIMESTAMP
        """
        await db.pool.execute(query, user_id, username)
    except Exception as e:
        logger.error(f"DB Error [register_user]: Failed to register user {user_id}. Details: {e}")

async def update_user_statistics(user_id: int, toxicity_score: float):
    """Updates the user's rolling averages and message counts."""
    try:
        query = """
            UPDATE users
            SET 
                total_messages = total_messages + 1,
                rolling_toxicity_avg = (
                    (rolling_toxicity_avg * total_messages) + $2
                ) / (total_messages + 1),
                last_seen = CURRENT_TIMESTAMP
            WHERE user_id = $1
        """
        await db.pool.execute(query, user_id, toxicity_score)
    except Exception as e:
        logger.error(f"DB Error [update_user_statistics]: {e}")

async def log_analyzed_message(data: dict):
    """Logs a message and triggers the user statistics update."""
    try:
        # Insert the message
        query = """
            INSERT INTO messages (
                message_id, guild_id, user_id, channel_id, 
                message_content, content_hash, sentiment_score, toxicity_score, 
                model_name, model_version
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """
        await db.pool.execute(
            query, 
            data.get('message_id'), 
            data.get('guild_id'), 
            data.get('user_id'), 
            data.get('channel_id'),
            data.get('message_content', ''),
            data.get('content_hash', 'no_hash_provided'),  # Added per feedback
            data.get('sentiment_score', 0.0),          
            data.get('toxicity_score', 0.0),           
            data.get('model_name', 'unknown_model'), 
            data.get('model_version', '1.0')
        )

        # Automatically update the user's running averages
        await update_user_statistics(
            data.get('user_id'),
            data.get('toxicity_score', 0.0)
        )

    except Exception as e:
        logger.error(f"DB Error [log_analyzed_message]: {e}")

async def get_recent_toxicity_stream(guild_id: int, limit: int = 20):
    """Provides a clean, rounded rolling window for the SPC engine."""
    try:
        query = """
            SELECT toxicity_score FROM messages 
            WHERE guild_id = $1 
            ORDER BY message_timestamp DESC 
            LIMIT $2
        """
        rows = await db.pool.fetch(query, guild_id, limit)
        # Round to 3 decimal places for cleaner math and dashboard UI
        return [round(row['toxicity_score'], 3) for row in rows]
    except Exception as e:
        logger.error(f"DB Error [get_recent_toxicity_stream]: {e}")
        return []

async def get_server_health_stats(guild_id: int):
    """Returns average sentiment and toxicity for the dashboard."""
    try:
        query = """
            SELECT 
                AVG(sentiment_score) as avg_sentiment,
                AVG(toxicity_score) as avg_toxicity,
                COUNT(*) as total_messages
            FROM messages 
            WHERE guild_id = $1
        """
        return await db.pool.fetchrow(query, guild_id)
    except Exception as e:
        logger.error(f"DB Error [get_server_health_stats]: {e}")
        return None

async def get_top_flagged_users(guild_id: int, limit: int = 5):
    """Returns the most toxic users. Uses correct LEFT JOIN logic."""
    try:
        query = """
            SELECT users.username, users.rolling_toxicity_avg, users.warning_count
            FROM users
            LEFT JOIN interventions 
                ON users.user_id = interventions.user_id AND interventions.guild_id = $1
            GROUP BY users.username, users.rolling_toxicity_avg, users.warning_count
            ORDER BY users.warning_count DESC
            LIMIT $2
        """
        return await db.pool.fetch(query, guild_id, limit)
    except Exception as e:
        logger.error(f"DB Error [get_top_flagged_users]: {e}")
        return []

async def log_intervention(guild_id: int, user_id: int, message_id: int, action_type: str, reasoning: str, severity_level: str, generated_response: str = None):
    """Logs the AI's action and increments the user's warning count."""
    try:
        # Log the intervention
        query = """
            INSERT INTO interventions (
                guild_id, user_id, trigger_message_id, action_type, 
                severity_level, reasoning, generated_response
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        await db.pool.execute(query, guild_id, user_id, message_id, action_type, severity_level, reasoning, generated_response)

        # Increment the warning count on the user profile
        await db.pool.execute("""
            UPDATE users
            SET warning_count = warning_count + 1
            WHERE user_id = $1
        """, user_id)

    except Exception as e:
        logger.error(f"DB Error [log_intervention]: {e}")