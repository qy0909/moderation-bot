### **Expected input**
```
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
```

### **Return**
```
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
```

### **Setup** *example*
1. get api from googleapis.github.io/python-genai/
2. numpy pandas scipy google-genai python-dotenv 

### **Step** *example*
1. fetch data by aggregator data (baseline data must be normal / healthy / in-control)
2. create aggregator instance and fit with data
3. create threshold instance
4. create generator instance
5. create moderator instance
6. output = await moderator.make_decision(msg, record=record fetched from fetch_user_message)

### **logic**
1. lambda : weight of current message against historical
2. current_ewma : lambda (current_cli) + (1-lambda) previous_ewma
3. current_cli : Prioritizes confidence intervals. If trust score > 0.7, use raw model scores; otherwise, apply dynamic penalties...reliable high>low , toxicity>sentiment>emotion => 0.5/0.3/0.2
4. normalize multiplier : This adjustment protects the system against hardcoded threshold degradation
5. ucl : current_ewma > thresholds
6. threshold : avg_baseline + norm_multiplier * std_baseline * sqrt(lambda/(2-lambda)) * (start_up) where start_up -> 1 when number of message -> infinity
7. sentiment -> [0,1] where A negative sentiment score results in a higher CLI value
8. emotion mapping : refered to PAD where -P , -D and +/-A is highly negative. P similars to sentiment score, -D {'anger', 'contempt','disgust'} 
