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
        
        # 2. Call analyze_text(content) to get toxicity score
        nlp_result = analyze_text(message_data["content"])
        
        # 3. Merge message_data + scores (Combine into one dict)
        record = {**message_data, **nlp_result}
        
        # 4. Call moderator.make_decision() (Gets the intervention decision)
        # Both parameter and return type in make_decision is dictionary
        decision = await self.moderator.make_decision(record)
        print(decision)
        
        # 5. Return result to event_handler (Bot sends the response)
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
