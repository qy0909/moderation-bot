# This is the main glue layer. It should do this in order:

# extract Discord message into shared format
# run analyze_text(content)
# prepare input for Moderator.make_decision(...)
# optionally fetch prior user state from DB
# save analyzed message
# save intervention if triggered
# return the result to event_handler.py
# Your shared message format should be:

class ModerationPipeline:
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
        
        
        return None
        