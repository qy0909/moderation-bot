from bot.config import Settings
from bot.event_handler import ModerationDiscordBot

# load settings
# fail early if token is missing
# create the bot client
# run it


def main():
    settings = Settings.from_env()
    if not settings.discord_token:
        raise RuntimeError("DISCORD_TOKEN is not set.")
    bot = ModerationDiscordBot(settings)
    bot.run(settings.discord_token)

if __name__ == "__main__":
    main()