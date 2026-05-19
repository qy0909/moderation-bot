# This is your Discord client. It should:

# initialize the moderation pipeline
# log on startup
# ignore bot messages
# pass user messages into the pipeline
# send a moderation reply if needed


class ModerationDiscordBot(discord.Client):
    def __init__(self, settings):
        super().__init__(intents=build_intents())
        self.settings = settings

    async def on_ready(self):
        ...

    async def on_disconnect(self):
        ...

    async def on_message(self, message):
        if message.author.bot:
            return
        result = await self.pipeline.handle_discord_message(message)
        if result and result["decision"]["generated_response"]:
            await message.channel.send(result["decision"]["generated_response"])