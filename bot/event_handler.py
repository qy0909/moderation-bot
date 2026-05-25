# This is your Discord client. It should:

# initialize the moderation pipeline
# log on startup
# ignore bot messages
# pass user messages into the pipeline
# send a moderation reply if needed

import discord
from bot.config import build_intents
from bot.pipeline import ModerationPipeline
from db.database import db
from bot.utils.logger import logger

# discord.Client means the bot inherits from discord.py built-in Client class
# Get standard Discord behaviour for free, this class add custom stuff on top
class ModerationDiscordBot(discord.Client):
    
    # __init__ — runs once when the bot is created
    def __init__(self, settings):
        super().__init__(intents=build_intents())   # calls the parent discord.Client's setup, and passes in the intents you built in config.py. This is how Discord knows what events to send your bot.
        self.settings = settings    #  saves the Settings object (your token, database URL, etc.) so the bot can use it later.
        self.pipeline = ModerationPipeline()
       
       
    # Discord calls them automatically when something happens: 
    # Bot successfully logged in and is online
    async def on_ready(self):
        await db.connect()
        
        # Register GUILD for new Discord server
        for guild in self.guilds:
            await db.pool.execute(
                "INSERT INTO moderation_settings (guild_id) VALUES ($1) ON CONFLICT DO NOTHING",
                guild.id
            )
        logger.info(f"Registered {len(self.guilds)} guild(s).")

        print("Bot is online.")

    # Bot lost connection to Discord 
    # on_disconnect: transient event (fires repeatedly, auto-recovers
    async def on_disconnect(self):
        # await db.disconnect() cannot do this
        logger.warning("Lost connection to Discord. Auto-reconnecting when network returns.")
        
    # close() = real shutdown (fires once)
    async def close(self):
        await db.disconnect()  
        logger.info("Bot shutting down, database closed.")
        await super().close()

    # A message was sent in any visible channel
    async def on_message(self, message):
        # 1. If the message author is a bot → ignore it and stop (prevents infinite loops)
        if message.author.bot:
            return
        
        # 2. Pass the message to your pipeline → get back a moderation result
        # await means: "do this, and wait for it to finish before continuing."
        
        # 2a. Before passing msg to pipeline, check 2 edge cases
        # Empty msg
        if not message.content:
            return
        if not message.content.strip():
            return
        
        # Msg too long
        if len(message.content) > 2000:  # Discord's own limit is 2000 characters, so this is a reasonable cap.
            return
        
        result = await self.pipeline.handle_discord_message(message)
        
        # 3. If the result contains a response → send it to the channel
        # message.channel.send() is how your bot posts a message.
        if result and result["decision"]["generated_response"]:
            await message.channel.send(result["decision"]["generated_response"])