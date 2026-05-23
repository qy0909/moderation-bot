from bot.moderation.response_generator import ResponseGenerator
from bot.analytics.threshold import ActionType, AdaptiveThreshold
from datetime import datetime, timezone
from bot.analytics.aggregation import Aggregator, EmotionType
from bot.utils.logger import logger

class Moderator:
    def __init__(self, aggregator, threshold,response_generator,):
        self.threshold = threshold
        self.aggregator = aggregator
        self.response_generator = response_generator

    async def make_decision(self,message:dict,record=None):
        # get message
        clean_message = self._clean_input(message)
        if clean_message is None:
            logger.warning(f'Invalid message! user_id :{getattr(message,"user_id","unknown")}')
            return
        
        # append new message into myList
        result = await self.aggregator.add_message(clean_message,record)
        if(len(result) == 0):
           logger.warning(f'Enqueue Failed! user_id :{getattr(clean_message,"user_id","unknown")}')
           return

        # make decision
        action_type = self._get_action_type(clean_message,result)
        if not action_type:
            logger.warning(f'Decide Failed! user_id :{getattr(clean_message,"user_id","unknown")}')
            action_type = ActionType.IGNORE

        # generate text if any
        reply = ''
        reason = ''
        
        if(action_type != ActionType.IGNORE):
            generated = await self.response_generator.generate_moderation_text(action_type=action_type, message_content=clean_message.get('message_content'))
            reply = generated["reply"]
            reason = generated["reason"]

        return {
            'user_id': clean_message.get('user_id'),
            'guild_id': clean_message.get('guild_id'),
            'channel_id':clean_message.get('channel_id'),
            'message_id': clean_message.get('message_id'),
            'action_type': action_type.value,
            'reasoning': reason,
            'generated_response': reply,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'metrics': { k.value: v for k,v in (self.threshold.get_thresholds(self.aggregator)).items()},
            'ewma': result.get('ewma')
        }

    def _clean_input(self, message:dict):
        try:
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
            return cleaned
        except (TypeError, ValueError, AttributeError):
            return None

    def _get_action_type(self,clean_message:dict,result):
    
        # get last message cli and ewma
        cli = result.get('cli')
        ewma = result.get('ewma')
        
        # get each threshold from Threshold
        thresholds = self.threshold.get_thresholds(self.aggregator)

        # get decision
        if not thresholds:
            logger.warning('Failed to calculate threshold')
            return ActionType.IGNORE

        if(ewma > thresholds.get(ActionType.ESCALATE)):
            return ActionType.ESCALATE
        elif(ewma > thresholds.get(ActionType.WARNING)):
            return ActionType.WARNING
        elif(ewma > thresholds.get(ActionType.SOFT_REMINDER)):
            return ActionType.SOFT_REMINDER
        else: return ActionType.IGNORE



                

    
