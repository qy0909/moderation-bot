import statistics
import pandas as pd
from bot.utils.logger import logger
from collections import deque

#from cal mean, std, and avg logic

class Aggregator:
    def __init__(self,guild_id,window_size=20):
        self.myList = deque(maxlen=window_size)
        self.guild_id = guild_id

    async def start_up(self,db):
        try:
            query = """
                SELECT toxicity_score, sentiment_score
                FROM messages
                WHERE guild_id = $1
                ORDER BY message_timestamp DESC 
                LIMIT $2
            """
            messages = await db.fetch(query,self.guild_id,self.myList.maxlen)

            if not messages:
                logger.info('Database is empty')
                return

            logger.info('Successfully loaded from database')

            records = [dict(r) for r in reversed(messages)]
            self.myList.extend(records)

        except Exception as e:
            logger.error(f'Failed to load data:{e}')

    def add_message(self,message):
        if (not message or message.get('toxicity_score') is None or message.get('sentiment_score') is None):
            logger.warning('Invalid message')
            return
        self.myList.append(message)

    def cal_statistic_toxicity(self):
        if(len(self.myList)<=2): return {}

        toxicities = [r['toxicity_score'] for r in self.myList]

        return {
            'rolling_avg_toxicity' : statistics.mean(toxicities),
            'rolling_std_toxicity' : statistics.stdev(toxicities)
        }
    def cal_statistic_sentiment(self):
        if(len(self.myList) <= 2): return {}

        sentiments = [r['sentiment_score'] for r in self.myList]

        return{
            'rolling_avg_sentiment' : statistics.mean(sentiments),
            'rolling_std_sentiment' : statistics.stdev(sentiments)
        }

    async def cal_hourly_average(self,db,hours=24):
        try:

            query = """
                SELECT 
                    date_trunc('hour', message_timestamp) AS hour, 
                    AVG(toxicity_score) AS avg_toxicity,
                    AVG(sentiment_score) AS avg_sentiment
                FROM messages
                WHERE message_timestamp > NOW() - INTERVAL '1 hour' * $1
                GROUP BY hour
                ORDER BY hour DESC;
            """

            records = await db.fetch(query, hours)
            return [dict(r) for r in records]

        except Exception as e:
            logger.error(f'Failed to load data: {e}')
    
    def get_server_metrics_report(self, threshold):

        tox_stats = self.cal_statistic_toxicity()
        
        if not tox_stats:
            return None
            
        ucl = threshold.cal_threshold(threshold.levels.WARNING)
        
        return {
            'guild_id': self.guild_id,
            'rolling_avg_toxicity': tox_stats['rolling_avg_toxicity'],
            'rolling_std_toxicity': tox_stats['rolling_std_toxicity'],
            'upper_control_limit': ucl,
            'messages_processed': len(self.myList)
        }


