import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from bot.moderation.intervention import Moderator
from bot.analytics.threshold import ActionType

@pytest.fixture
def mock_dependencies():
    threshold_mock = MagicMock()
    # Mocking standard threshold cuts
    threshold_mock.get_thresholds.return_value = {
        ActionType.IGNORE: 0.10,
        ActionType.SOFT_REMINDER: 0.30,
        ActionType.WARNING: 0.50,
        ActionType.ESCALATE: 0.75
    }
    
    response_gen_mock = AsyncMock()
    response_gen_mock.generate_moderation_text.return_value = "Please keep the conversation civil."
    
    aggregator_mock = AsyncMock()
    
    return threshold_mock, response_gen_mock, aggregator_mock


class TestModeratorIntervention:

    def test_input_cleaning_and_bounding(self, mock_dependencies):
        th, rg, agg = mock_dependencies
        mod = Moderator(threshold=th, response_generator=rg, aggregator=agg)
        
        raw_dirty_msg = {
            'guild_id': 'g1', 'channel_id': 'c1', 'user_id': 'u1', 'message_id': 'm1',
            'text': 'Hello world',
            'toxicity': 1.5,
            'toxicity_confidence': -0.5,
            'sentiment': -2.0,
            'sentiment_confidence': 1.2,
            'emotion': 'anger',
            'emotion_confidence': 0.8
        }
        
        cleaned = mod._clean_input(raw_dirty_msg)
        
        assert cleaned['toxicity_score'] == 1.0
        assert cleaned['toxicity_confidence'] == 0.0
        assert cleaned['sentiment_score'] == -1.0
        assert cleaned['sentiment_confidence'] == 1.0
        assert cleaned['emotion'] == 'anger'

    @pytest.mark.asyncio
    async def test_make_decision_ignore_action(self, mock_dependencies):
        th, rg, agg = mock_dependencies
        mod = Moderator(threshold=th, response_generator=rg, aggregator=agg)
        
        # Mocking values falling under IGNORE cutoff
        agg.add_message.return_value = {'cli': 0.05, 'ewma': 0.12}
        
        msg = {'guild_id': '1', 'channel_id': '1', 'user_id': '1', 'message_id': '1', 'text': 'Fine'}
        output = await mod.make_decision(msg)
        
        assert output['action_type'] == ActionType.IGNORE.value
        assert output['generated_response'] == ''  # No text generated for IGNOREs
        rg.generate_moderation_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_make_decision_warning_trigger(self, mock_dependencies):
        th, rg, agg = mock_dependencies
        mod = Moderator(threshold=th, response_generator=rg, aggregator=agg)
        
        # 0.65 falls between WARNING (0.50) and ESCALATE (0.75)
        agg.add_message.return_value = {'cli': 0.70, 'ewma': 0.65}
        
        msg = {'guild_id': '1', 'channel_id': '1', 'user_id': '1', 'message_id': '1', 'text': 'Bad toxic words'}
        output = await mod.make_decision(msg)
        
        assert output['action_type'] == ActionType.WARNING.value
        assert output['generated_response'] == "Please keep the conversation civil."
        rg.generate_moderation_text.assert_called_once_with(
            action_type=ActionType.WARNING, 
            message_content='Bad toxic words'
        )

    @pytest.mark.asyncio
    async def test_make_decision_escalate_trigger(self, mock_dependencies):
        th, rg, agg = mock_dependencies
        mod = Moderator(threshold=th, response_generator=rg, aggregator=agg)
        
        agg.add_message.return_value = {'cli': 0.90, 'ewma': 0.82}
        
        msg = {'guild_id': '1', 'channel_id': '1', 'user_id': '1', 'message_id': '1', 'text': 'Extreme text'}
        output = await mod.make_decision(msg)
        
        assert output['action_type'] == ActionType.ESCALATE.value
        rg.generate_moderation_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_input_fails_gracefully(self, mock_dependencies):
        th, rg, agg = mock_dependencies
        mod = Moderator(threshold=th, response_generator=rg, aggregator=agg)
    
        output = await mod.make_decision(None)
        
        assert output is None
        
        agg.add_message.assert_not_called()


    @pytest.mark.asyncio
    async def test_enqueue_failure_returns_none(self, mock_dependencies):
        th, rg, agg = mock_dependencies
        mod = Moderator(threshold=th, response_generator=rg, aggregator=agg)
        
        # Mocking an aggregator pipeline enqueue failure resulting in blank dict return
        agg.add_message.return_value = {}
        
        msg = {'guild_id': '1', 'channel_id': '1', 'user_id': '1', 'message_id': '1', 'text': 'Test'}
        output = await mod.make_decision(msg)
        
        assert output is None
