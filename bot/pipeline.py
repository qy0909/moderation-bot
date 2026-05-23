# This is the main glue layer. It should do this in order:

# extract Discord message into shared format
# run analyze_text(content)
# prepare input for Moderator.make_decision(...)
# optionally fetch prior user state from DB
# save analyzed message
# save intervention if triggered
# return the result to event_handler.py
# Your shared message format should be:

from bot.moderation.analyzer import analyze_text
from bot.analytics.aggregation import Aggregator
from bot.analytics.threshold import AdaptiveThreshold
from bot.moderation.response_generator import ResponseGenerator
from bot.moderation.intervention import Moderator
from db.database import db

from bot.analytics.aggregation import AggregatorData

from db.queries import register_user, log_analyzed_message, log_intervention

class ModerationPipeline:
    
    def __init__(self):
        # aggregator, threshold, response_generator are local variables, created temporarily
        # get passed into Moderator(...) immediately
        aggregator = Aggregator()
        threshold = AdaptiveThreshold()
        response_generator = ResponseGenerator()
        self.moderator = Moderator(aggregator, threshold, response_generator)  # only this needs to be saved bcs handle_discord_message will use
    
    async def handle_discord_message(self, message):
        
        # 1. Convert the Discord message object into a plain dict
        message_data = {
            "message_id": str(message.id),
            "guild_id": str(message.guild.id),
            "user_id": str(message.author.id),
            "username": str(message.author),
            "channel_id": str(message.channel.id),
            "content": message.content,
            "timestamp": message.created_at.isoformat(),
        }
        
        # Discord IDs are strings in the shared format, but the DB uses BIGINT.
        # Convert once here, then use these for every DB call below.
        user_id = int(message_data["user_id"])
        guild_id = int(message_data["guild_id"])
        channel_id = int(message_data["channel_id"])
        message_id = int(message_data["message_id"])

        
        # 2. Call analyze_text(content) to get toxicity score
        try:
            nlp_result = analyze_text(message_data["content"])
        except Exception as e:
            print(f"NLP analysis failed: {e}")
            return None # Give up on this msg, don't crash the bot
        
        # 3. Merge message_data + scores (Combine into one dict)
        record = {**message_data, **nlp_result}
        
        # 4. Fetch user history before make_decision()
        aggregator_data = AggregatorData(message_data["channel_id"], message_data["guild_id"])
        user_record = await aggregator_data.fetch_user_messages(db.pool, user_id)
        
        # 5. Call moderator.make_decision() (Gets the intervention decision)
        # Both parameter and return type in make_decision is dictionary
        try:
            decision = await self.moderator.make_decision(record, record=user_record)
            print(decision)
        except Exception as e:
            print(f"Moderation decision failed: {e}")
            return None  # return None bcs if result is None, the if is False (inside event_handler), the bot stays silent instead of crashing. That's the graceful behaviour
        
        # 6. Save to database
        try:
            record["message_id"] = message_id
            record["guild_id"] = guild_id
            record["user_id"] = user_id
            record["channel_id"] = channel_id
            
            if decision:
                record["ewma"] = decision["ewma"]
            
            await register_user(user_id, message_data["username"])
            
            # Bridging analyzer.py return part & log_analyzed_message return part
            record["message_content"] = record["content"]
            
            # Decide the flag
            record["is_flagged"] = bool(decision and decision["action_type"] != "ignore")
            
            # Insert record to message table
            await log_analyzed_message(record)
            
            # Insert record to intervention table
            if decision and decision["action_type"] != "ignore":
                
                severity_map = {
                    "soft_reminder": "low",
                    "warning": "high",
                    "escalate": "critical"
                }

                await log_intervention(
                    guild_id=guild_id,
                    user_id=user_id,
                    message_id=message_id,
                    action_type=decision["action_type"],
                    reasoning=decision["reasoning"],
                    severity_level=severity_map.get(decision["action_type"], "low"),
                    generated_response=decision["generated_response"]
                )
            
        except Exception as e:
            print(f"Database error: {e}") # db error shouldn't stop the bot from replying
        
        # 7. Return result to event_handler (Bot sends the response)
        return {"decision": decision}
   

'''
User types a message
        ↓
analyze_text()        → "this message has 0.8 toxicity, -0.5 sentiment, anger emotion"
        ↓
Aggregator            → "looking at this user's history, their overall score is rising"
        ↓
AdaptiveThreshold     → "that score crosses the WARNING threshold"
        ↓
Response_generator    → "here's an AI-written warning message"
        ↓
Bot sends the warning




What each piece does:

Aggregator — tracks each user's behaviour over time. 
It doesn't just look at one message — it looks at the pattern. 
Someone who sends 10 slightly toxic messages gets flagged even if no single message 
crosses the limit. 
It calculates a score called EWMA (a rolling average that weighs recent messages more).
- Aggregator()   # no required arguments, uses sensible defaults


AdaptiveThreshold — decides what action to take based on the EWMA score. 
It compares the score against statistical thresholds to choose one of:
IGNORE — nothing wrong
SOFT_REMINDER — gentle nudge
WARNING — clear warning
ESCALATE — serious violation
- AdaptiveThreshold()   # no required arguments


Response_generator — uses Google Gemini AI to write the actual warning message. 
It needs a GENERATIVE_AI_API key in your .env file 
(like your Discord token, but for Google AI).
- Response_generator()   # reads GENERATIVE_AI_API from .env automatically


Moderator — the coordinator. It takes all three above and runs them in sequence 
when make_decision() is called:
- Moderator(threshold, response_generator, aggregator)

'''


'''
FOR DATABASE PART,
Save guild (moderation_settings) -> in event_handler.py on_ready()
Register user -> pipeline.py when message is sent to produce result
Save message (log analyzed msg) -> pipeline.py
Save intervention if available (log intervention) -> pipeline.py

DATABASE STRUCTURE
guild_id   = which Discord server
user_id    = who sent the message  
message_id = the specific message
channel_id = which channel it was sent in

THE CHAIN
moderation_settings (guild must exist first)
    ↓
users (user must exist first)
    ↓
messages (both guild and user must exist first)
    ↓
interventions (guild, user, and message must all exist first)


'''
