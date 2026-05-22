'''
Path(__file__) — the path of the current test file
.parents[1] — go up 2 levels: test_pipeline.py → tests/ → project root
sys.path.insert(0, ...) — tells Python "also look for modules here"
'''
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from bot.pipeline import ModerationPipeline




# Create a fake Discord message using MagicMock
@pytest.fixture
def fake_message():
    message = MagicMock()
    message.id = 123456
    message.content = "You are so stupid"
    message.author.id = 111
    message.author.bot = False
    message.author.__str__ = lambda self: "testuser#0001"
    message.guild.id = 999
    message.channel.id = 777
    message.created_at.isoformat.return_value = "2026-01-01T00:00:00"
    return message

# Create a ModerationPipeline with mocked internals (so it doesn't call real APIs)
# Call handle_discord_message(fake_message)
@pytest.mark.asyncio
async def test_pipeline_returns_decision(fake_message):
    pipeline = ModerationPipeline()
    result = await pipeline.handle_discord_message(fake_message)
    assert result is not None
    assert "decision" in result

# Check the result has the right structure
@pytest.mark.asyncio
async def test_pipeline_returns_none_on_nlp_failure(fake_message):
    with patch("bot.pipeline.analyze_text", side_effect=Exception("API down")):
        pipeline = ModerationPipeline()
        result = await pipeline.handle_discord_message(fake_message)
        assert result is None
