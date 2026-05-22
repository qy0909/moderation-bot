# This is your Discord client. It should:

# initialize the moderation pipeline
# log on startup
# ignore bot messages
# pass user messages into the pipeline
# send a moderation reply if needed

import discord
from bot.config import build_intents
from bot.pipeline import ModerationPipeline

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
        print("Bot is online.")

    # Bot lost connection to Discord
    async def on_disconnect(self):
        print("Bot is disconnected.")

    # A message was sent in any visible channel
    async def on_message(self, message):
        # 1. If the message author is a bot → ignore it and stop (prevents infinite loops)
        if message.author.bot:
            return
        
        # 2. Pass the message to your pipeline → get back a moderation result
        # await means: "do this, and wait for it to finish before continuing."
        result = await self.pipeline.handle_discord_message(message)
        
        # 3. If the result contains a response → send it to the channel
        # message.channel.send() is how your bot posts a message.
        if result and result["decision"]["generated_response"]:
            await message.channel.send(result["decision"]["generated_response"])