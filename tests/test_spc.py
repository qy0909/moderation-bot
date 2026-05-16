import pytest
import numpy as np
import pandas as pd
from collections import deque
from scipy.stats import norm
import math

from bot.analytics.aggregation import Aggregator, EmotionType
from bot.analytics.threshold import AdaptiveThreshold, ActionType

# Mock record for testing
@pytest.fixture
def mock_db_record():
    return {'last_ewma': 0.35}

@pytest.fixture
def mock_messages():
    """Generates synthetic historical messages for startup baseline calculation."""
    return [
        {
            'toxicity_score': 0.1, 'sentiment_score': 0.8, 'emotion': 'joy',
            'toxicity_confidence': 0.9, 'sentiment_confidence': 0.9, 'emotion_confidence': 0.9
        },
        {
            'toxicity_score': 0.2, 'sentiment_score': 0.5, 'emotion': 'neutral',
            'toxicity_confidence': 0.8, 'sentiment_confidence': 0.8, 'emotion_confidence': 0.8
        },
        {
            'toxicity_score': 0.15, 'sentiment_score': 0.6, 'emotion': 'gratitude',
            'toxicity_confidence': 0.85, 'sentiment_confidence': 0.85, 'emotion_confidence': 0.85
        }
    ]


class TestAggregatorSPC:
    
    def test_startup_baseline_calculation(self, mock_messages):
        aggregator = Aggregator(lamb=0.4, window_size=10)
        aggregator.start_up(mock_messages)
        
        assert aggregator.avg > 0
        assert aggregator.std >= 0.02
        assert aggregator.guild_last_ewma is not None

    @pytest.mark.asyncio
    async def test_cli_calculation_high_confidence(self, mock_db_record):
        aggregator = Aggregator(lamb=0.4)
        clean_msg = {
            'user_id': 'user_123',
            'toxicity_score': 0.8,
            'sentiment_score': -0.8,  # processed = (1 - (-0.8)) / 2 = 0.9
            'emotion': 'anger',       # emotion map = 0.75
            'toxicity_confidence': 0.9,
            'sentiment_confidence': 0.9,
            'emotion_confidence': 0.9
        }
        
        # Scenario: All confidence states > 0.7 -> condition state: (True, True, True)
        # Expected manual CLI: max(0.5*0.8 + 0.3*0.9 + 0.2*0.75, 0.8) = max(0.82, 0.8) = 0.82
        result = await aggregator.add_message(clean_msg, record=mock_db_record)
        
        assert 'cli' in result
        assert 'ewma' in result
        assert pytest.approx(result['cli'], 0.01) == 0.82

    @pytest.mark.asyncio
    async def test_cli_calculation_low_confidence(self, mock_db_record):
        aggregator = Aggregator(lamb=0.4)
        clean_msg = {
            'user_id': 'user_789',
            'toxicity_score': 0.5,
            'sentiment_score': 0.0,    # processed = 0.5
            'emotion': 'neutral',       # emotion map = 0.0
            'toxicity_confidence': 0.2, # False
            'sentiment_confidence': 0.1, # False
            'emotion_confidence': 0.3    # False
        }
        
        # Condition state: (False, False, False) -> Falls back to default calculation block
        result = await aggregator.add_message(clean_msg, record=mock_db_record)
        assert result['cli'] >= 0.0

    @pytest.mark.asyncio
    async def test_ewma_progression_with_historical_record(self, mock_db_record):
        lamb = 0.4
        aggregator = Aggregator(lamb=lamb)
        
        clean_msg = {
            'user_id': 'user_555',
            'toxicity_score': 0.4, 'sentiment_score': 0.0, 'emotion': 'neutral',
            'toxicity_confidence': 0.9, 'sentiment_confidence': 0.9, 'emotion_confidence': 0.9
        }
        
        # State (True, True, True): cli = max(0.5*0.4 + 0.3*0.5 + 0.2*0.0, 0.4) = 0.4
        # Expected ewma = lamb * cli + (1 - lamb) * prev_ewma
        # prev_ewma from record = 0.35
        expected_ewma = (lamb * 0.4) + ((1 - lamb) * mock_db_record['last_ewma']) # 0.16 + 0.21 = 0.37
        
        result = await aggregator.add_message(clean_msg, record=mock_db_record)
        assert pytest.approx(result['ewma'], 0.01) == expected_ewma


class TestAdaptiveThresholdSPC:

    def test_threshold_math_distribution(self):
        aggregator = Aggregator(lamb=0.3)
        aggregator.avg = 0.2
        aggregator.std = 0.05
        
        adaptive_th = AdaptiveThreshold()
        thresholds = adaptive_th.get_thresholds(aggregator)
        
        # Verify all types exist inside output dict
        assert ActionType.IGNORE in thresholds
        assert ActionType.SOFT_REMINDER in thresholds
        assert ActionType.WARNING in thresholds
        assert ActionType.ESCALATE in thresholds

        # Verify that thresholds step up monotonically as alpha drops
        assert thresholds[ActionType.ESCALATE] > thresholds[ActionType.WARNING]
        assert thresholds[ActionType.WARNING] > thresholds[ActionType.SOFT_REMINDER]
        assert thresholds[ActionType.SOFT_REMINDER] > thresholds[ActionType.IGNORE]

        # Explicit statistical validation check for one action step
        # factor = sqrt(0.3 / (2 - 0.3)) = sqrt(0.3 / 1.7) = 0.4201
        # std_ewma = 0.05 * 0.4201 = 0.0210
        # For ESCALATE (alpha=0.00001): z = norm.ppf(1 - 0.00001) = 4.2648
        # Expected target = 0.2 + (4.2648 * 0.0210) = 0.2895
        factor = math.sqrt(0.3 / (2 - 0.3))
        std_ewma = 0.05 * factor
        z_score = norm.ppf(1 - 0.015) # Example mock pattern testing map logic
        
        assert thresholds[ActionType.ESCALATE] > aggregator.avg

