from bot.moderation.response_generator import Response_generator

# get ucl
class Moderator:
    def __init__(self,threshold,response_generator):
        self.threshold = threshold
        self.response_generator = response_generator

    def make_decision(self,message,user):
        self.threshold.aggregator.add_message(message)
        toxicity = message.get('toxicity_score')
        sentiment = message.get('sentiment_score')
        warning_line = self.threshold.cal_threshold(self.threshold.levels.WARNING)

        is_anomaly = toxicity >= warning_line
        is_negative_sentiment = sentiment <= -0.6
        severity_level = 'low'
        action_type = 'ignore'

        if((message.get('confidence')<0.5 or toxicity<=self.threshold.static or len(self.threshold.aggregator.myList) <= 10 or toxicity <= self.threshold.cal_threshold(self.threshold.levels.IGNORE)) and not is_negative_sentiment):
            return self.get_intervention_result(user,action_type,severity_level,is_anomaly,'')

        else:
            severity_level = 'low'
            action_type = 'ignore'
            if(is_anomaly):
                if(user.get('warning_count') >= 3):
                    action_type = 'escalate'
                    severity_level = 'critical'
                else:
                    action_type = 'warning'
                    severity_level = 'high'
            else:
                action_type = 'soft_reminder'
                severity_level = 'medium'
            reply = self.response_generator.generate_moderation_text(action_type,message.get('message_content'))

        return self.get_intervention_result(user,action_type,severity_level,is_anomaly,reply)

    def _get_intervention_result(user,action_type,severity_level,is_anomaly,reply):
        return {
                'user_id': user.get('user_id'),
                'guild_id':self.threshold.aggregator.guild_id,
                'action_type': action_type,
                'severity_level': severity_level,
                'is_anomaly':is_anomaly,
                'reply':reply,
            }
