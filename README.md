### **Expected input**
## cleaned = {
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

### **Return**
##     {
            'user_id': clean_message.get('user_id'),
            'guild_id': clean_message.get('guild_id'),
            'channel_id':clean_message.get('channel_id'),
            'message_id': clean_message.get('message_id'),
            'action_type': action_type.value,
            'generated_response': reply,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'metrics': { k.value: v for k,v in (self.threshold.get_thresholds(self.aggregator)).items()}
      }
