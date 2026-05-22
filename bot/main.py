from bot.config import Settings
from bot.event_handler import ModerationDiscordBot

# load settings
# fail early if token is missing
# create the bot client
# run it


def main():
    settings = Settings.from_env()
    if not settings.discord_token:   # Read the env file and create a settings object holding token and db url
        raise RuntimeError("DISCORD_TOKEN is not set.")
    bot = ModerationDiscordBot(settings)   # Create the bot, passing in the settings. This is where event_handler.py's __init__ runs.
    bot.run(settings.discord_token)        # Start the bot. This connects to Discord using your token and keeps running forever (listening for messages). This line never returns until you stop the bot.

if __name__ == "__main__":   # only run main() if this file is executed directly,  (e.g. python -m bot.main), not if it's imported by another file.
    main()