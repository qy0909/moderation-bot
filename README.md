### **Expected input**
```cleaned = {
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
}```

### **Return**
{
        'user_id': clean_message.get('user_id'),
        'guild_id': clean_message.get('guild_id'),
        'channel_id':clean_message.get('channel_id'),
        'message_id': clean_message.get('message_id'),
        'action_type': action_type.value,
        'generated_response': reply,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'metrics': { k.value: v for k,v in (self.threshold.get_thresholds(self.aggregator)).items()}
}

### **Setup** *example*
- #### get api from googleapis.github.io/python-genai/
- #### numpy pandas scipy google-genai python-dotenv 

### **Class**
#### AggregatorData(channel_id,guild_id)
- ##### fetch_start_up_message from message db used by start_up()
- ##### fetch_user_message from users db used by add_message(,record), make_decision(,record) **!!! last_ewma is required !!!**
- ##### cal_hourly_average from message db return avg toxicity_score and sentiment_score

#### Aggregator(lamb,window_size) !!! lambda : weight of current data !!!
- ##### start_up(messages)
- ##### add_message(clean_message, record) return {cli, ewma} used by _get_action_type(,result)

#### AdaptiveThreshold
- ##### get_thresholds return { ActionType.IGNORE: w, ...., ActionType.ESCALATE: z }

#### Moderator(adaptive_threshold, aggregator, response_generator)
- ##### make_decision(raw_message,record) return output

#### Response_generator(environment_path,api)
- ##### generate_moderation_text(ActionType, message_content)

### **Step** *example*
1. fetch data by aggregator data
2. create aggregator instance and fit with data
3. create threshold instance
4. create generator instance
5. create moderator instance
6. output = await moderator.make_decision(msg, record=record fetch from fetch_user_message)

