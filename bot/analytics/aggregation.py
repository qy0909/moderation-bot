import pandas as pd
import math
import weakref
import asyncio
import numpy as np
from bot.utils.logger import logger
from collections import defaultdict,deque
from enum import StrEnum,auto
"""
    cleaned = {
        'guild_id': message.get('guild_id'),
        'channel_id': message.get('channel_id'),
        'user_id': message.get('user_id'),
        'message_id': message.get('message_id'),
        'message_content': str(message.get('text','')),
        'toxicity_score': max(0.0, min(1.0, float(message.get('toxicity', 0)))),
        'toxicity_confidence': max(0.0, min(1.0,float(message.get('toxicity_confidence', 0)))),
        'sentiment_score': max(-1.0, min(1.0, float(message.get('sentiment', 0)))),
        'sentiment_confidence': max(0.0, min(1.0, float(message.get('sentiment_confidence', 0)))),
        'emotion': str(message.get('emotion', 'neutral')),
        'emotion_confidence': max(0.0, min(1.0, float(message.get('emotion_confidence', 0))))
    }
"""
class EmotionType(StrEnum):
    ANGER = auto()
    CONTEMPT = auto()
    DISGUST = auto()
    FEAR = auto()
    FRUSTRATION = auto() 
    GRATITUDE = auto()
    JOY = auto()
    LOVE = auto()
    NEUTRAL = auto()
    SADNESS = auto()
    SURPRISE = auto()

class Aggregator:
    def __init__(self,lamb=0.40,window_size=50):
        self.lamb = lamb
        self.window_size = window_size
        self.user_buffers = defaultdict(lambda: deque(maxlen=self.window_size))
        self.emotion_map = {
            EmotionType.CONTEMPT.value: 0.95,
            EmotionType.DISGUST.value: 0.85,
            EmotionType.ANGER.value: 0.75,
            EmotionType.FEAR.value: 0.55,
            EmotionType.SADNESS.value: 0.50,
            EmotionType.FRUSTRATION.value: 0.35,
            EmotionType.NEUTRAL.value: 0.00,
            EmotionType.SURPRISE.value: 0.02,
            EmotionType.GRATITUDE.value: 0.02,
            EmotionType.JOY.value: 0.01,
            EmotionType.LOVE.value: 0.00,
        }
        self.user_locks = {}
        self.avg = 0.5
        self.std = 0.1
        self.guild_last_ewma = self.avg
        self.user_last_ewmas = defaultdict(lambda : self.guild_last_ewma)

    # normal message
    def start_up(self,messages):
        # fetch normal messages to calculate the baseline
        if not messages:
            logger.info('Database is empty')
            return

        logger.info('Successfully loaded from database')

        df = pd.DataFrame([dict(r) for r in messages][::-1])
        df['s_processed'] = (1 - df['sentiment_score']) / 2
        df['e_processed'] = df['emotion'].map(self.emotion_map).fillna(0.0)

        t_s = df['toxicity_score']
        t_c = df['toxicity_confidence']
        s_s = df['s_processed']
        s_c = df['sentiment_confidence']
        e_s = df['e_processed']
        e_c = df['emotion_confidence']

        # reliable scores
        t_ok = t_c > 0.7
        s_ok = s_c > 0.7
        e_ok = e_c > 0.7

        # 2 * 2 * 2 conditions
        conditions = [
            t_ok & s_ok & e_ok,
            t_ok & s_ok & ~e_ok,
            t_ok & ~s_ok & e_ok,
            t_ok & ~s_ok & ~e_ok,
            ~t_ok & s_ok & e_ok,
            ~t_ok & s_ok & ~e_ok,
            ~t_ok & ~s_ok & e_ok,
            ~t_ok & ~s_ok & ~e_ok
        ]
        # by default t/s/e = 0.5/0.3/0.2 dec if not trustable
        choices = [
            np.maximum(0.5 * t_s + 0.3 * s_s + 0.2 * e_s, t_s),
            np.maximum((0.5 * t_s + 0.3 * s_s + 0.2 * e_s * e_c) / (0.5 + 0.3 + 0.2 * e_c), t_s),
            np.maximum((0.5 * t_s + 0.2 * s_s * s_c + 0.3 * e_s ) / (0.5 + 0.2 * s_c + 0.3), t_s),
            np.maximum((0.5 * t_s + 0.3 * s_s * s_c + 0.2 * e_s * e_c) / (0.5 + 0.3 * s_c + 0.2 * e_c), t_s),

            (0.2 * t_c * t_s + 0.5 * s_s + 0.3 * e_s) / (0.2 * t_c + 0.5 + 0.3),
            (0.3 * t_c * t_s + 0.5 * s_s + 0.2 * e_s * e_c) / (0.3 * t_c + 0.5 + 0.2 * e_c),
            (0.3 * t_c * t_s + 0.2 * s_s * s_c + 0.5 * e_s) / (0.3 * t_c + 0.2 * s_c + 0.5),
            (0.5 * t_c * t_s + 0.3 * s_c * s_s + 0.2 * e_c * e_s) / (0.5 * t_c + 0.3 * s_c + 0.2 * e_c)
        ]

        # cal cli
        df['cli'] = np.select(conditions, choices, default=0.0)

        backup_score = 0.5 * t_s + 0.3 * s_s + 0.2 * e_s
        df['cli'] = df['cli'].fillna(backup_score)

        df['cli'] = np.maximum(df['cli'], 0.0)

        # cal ewma
        df['ewma'] = df['cli'].ewm(alpha=self.lamb, adjust=False).mean()

        #get mu / std
        self.avg = float(df['cli'].mean())
        self.std = float(max(df['cli'].std(), 0.02))

        # get last ewma    
        self.guild_last_ewma = df['ewma'].iloc[-1] if not df.empty else self.avg
        self.user_last_ewmas = defaultdict(lambda: self.guild_last_ewma)


    async def add_message(self,clean_message:dict,record):

        # check keys
        required_keys = {'user_id','toxicity_score','sentiment_score','emotion','toxicity_confidence','sentiment_confidence','emotion_confidence'}
        
        if not required_keys.issubset(set(clean_message.keys())):
            logger.warning(f"Missing keys in message: {required_keys - clean_message.keys()}")
            return {}

        user_id = clean_message['user_id']

        lock = self.user_locks.setdefault(user_id, asyncio.Lock())

        async with lock:
            # check record:
            if not record:
                logger.info(f'user_id : {user_id} historical message not found!')

            # access required data
            t_s = clean_message['toxicity_score']
            s_s = (1-clean_message['sentiment_score'])/2
            e_s = self.emotion_map.get(clean_message['emotion'],0.0)
            t_c = clean_message['toxicity_confidence']
            s_c = clean_message['sentiment_confidence']
            e_c = clean_message['emotion_confidence']

            state = (t_c > 0.7, s_c > 0.7 , e_c > 0.7)

            # same logic
            if state == (True, True, True):
                cli = (0.5 * t_s + 0.3 * s_s + 0.2 * e_s)
                cli = max(cli, t_s)
            elif state == (True, True, False):
                cli = (0.5 * t_s + 0.3 * s_s + 0.2 * e_s * e_c ) / (0.5 + 0.3 + (0.2 * e_c))
                cli = max(cli, t_s)
            elif state == (True, False, True):
                cli = (0.5 * t_s + 0.2 * s_s * s_c + 0.3 * e_s ) / (0.5 + (0.2 * s_c) + 0.3)
                cli = max(cli, t_s)
            elif state == (True, False, False):
                cli = (0.5 * t_s + 0.3 * s_s * s_c + 0.2 * e_s * e_c ) / (0.5 + (0.3 * s_c) + (0.2 * e_c))
                cli = max(cli, t_s)
            elif state == (False, True, True):
                cli = ( 0.2 * t_s * t_c + 0.5 * s_s + 0.3 * e_s) / (0.2 * t_c + 0.5 + 0.3)
            elif state == (False, True, False):
                cli = ( 0.3 * t_s * t_c + 0.5 * s_s + 0.2 * e_s * e_c) / ((0.3 * t_c) + 0.5 + (0.2 * e_c))
            elif state == (False, False, True):
                cli = (0.3 * t_s * t_c + 0.2 * s_s * s_c + 0.5 * e_s ) / ((0.3 * t_c) + (0.2 * s_c) + 0.5)
            else:
                cli = (0.5 * t_s * t_c + 0.3 * s_s * s_c + 0.2 * e_s * e_c ) / ((0.5 * t_c) + (0.3 * s_c) + (0.2 * e_c))

            user_id = clean_message['user_id']
            user_buffer = self.user_buffers[user_id]

            if len(user_buffer) > 0:
                prev_ewma = float(user_buffer[-1].get('ewma', self.user_last_ewmas[user_id]))
            else:
                if record and record['last_ewma'] is not None:
                    prev_ewma = float(record['last_ewma'])
                else:
                    prev_ewma = float(self.user_last_ewmas[user_id])

            ewma = self.lamb * cli + (1 - self.lamb) * prev_ewma

            self.user_last_ewmas[user_id] = ewma

            user_buffer.append({**clean_message, 'ewma': ewma, 'cli': cli})

            return {'ewma': ewma, 'cli': cli}

    
class AggregatorData:
    def __init__(self,channel_id,guild_id):
        self.guild_id = guild_id
        self.channel_id = channel_id

    async def fetch_start_up_message(self,messages_db):
        try:
            query = """
                SELECT toxicity_score, sentiment_score, emotion, toxicity_confidence, sentiment_confidence, emotion_confidence
                FROM messages
                WHERE guild_id = $1 AND
                    channel_id = $2 AND
                    toxicity_score < 0.6 AND
                    sentiment_score > -0.5 AND
                    NOT (LOWER(emotion) IN ('contempt','anger','disgust') AND emotion_confidence > 0.7)
                ORDER BY message_timestamp DESC
                LIMIT $3
            """
            messages = await messages_db.fetch(query,self.guild_id,self.channel_id,200)
            return messages
        except Exception as e:
            logger.error(f'Failed to load data:{e}')
            return []

    async def fetch_user_messages(self,user_db,user_id):
        try:
            record = await user_db.fetchrow(
                    "SELECT last_ewma FROM users WHERE user_id = $1 ORDER BY last_seen DESC LIMIT 1", 
                    user_id
                )
            return record
        except Exception as e:
            logger.error(f'Failed to load data: {e}')
            return None

    async def cal_hourly_average(self,messages_db,hours=24):
        try:
            query = """
                SELECT 
                    date_trunc('hour', message_timestamp) AS hour, 
                    AVG(toxicity_score) AS avg_toxicity,
                    AVG(sentiment_score) AS avg_sentiment
                FROM messages
                WHERE (message_timestamp > NOW() - ($1 * INTERVAL '1 hour')) AND
                    guild_id = $2 AND
                    channel_id = $3
                GROUP BY hour
                ORDER BY hour DESC;
            """
            records = await messages_db.fetch(query,hours,self.guild_id,self.channel_id)
            return [dict(r) for r in records]

        except Exception as e:
            logger.error(f'Failed to load data: {e}')
            return []
