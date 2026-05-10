from bot.moderation.analyzer import analyze_text

messages = [
    "Hello everyone",
    "Great work team",
    "You are stupid",
    "This is awful",
    "bro ni memang annoying gila"
]

for msg in messages:
    print(analyze_text(msg))