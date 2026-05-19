from dataclasses import dataclass
import os
import discord
from dotenv import load_dotenv

# It should do two things:

# load .env
# create Discord intents with message_content=True

load_dotenv()

@dataclass
class Settings:
    discord_token: str | None
    database_url: str | None

    @classmethod
    def from_env(cls):
        return cls(
            discord_token=os.getenv("DISCORD_TOKEN"),
            database_url=os.getenv("DATABASE_URL"),
        )

def build_intents():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.messages = True
    return intents