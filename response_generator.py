import os
import json
from bot.utils.logger import logger
from dotenv import load_dotenv
from google import genai
from google.genai import types

class Response_generator:
    def __init__(self, environment_path='.env', api_name='GENERATIVE_AI_API'):
        load_dotenv(environment_path)
        API = os.getenv(api_name)
        self.api_key = API
        self.model="gemini-3-flash-preview"
        self.system_instruction="""
                You are a Content Moderation System. 
                1. Objective: Analyze user input for safety violations or negative sentiment.
                2. Logic: Perform an internal Step-by-step reasoning before making a decision. 
                3. Output: Return the result in valid JSON format ONLY. 
                    Fields: 
                    - "reason": Scientific explanation of the violation.
                    - "reply": The actual response string to be shown to the user.
                4. Tone: Remain strictly objective and neutral.
                """
        self.safe_config = [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            )
        ]
        self.response_mime_type="application/json"
        self.client = self._init_client()
    
    def _init_client(self):
        try:
            if not self.api_key:
                logger.warning('Failed to get api key')
                return None
            return genai.Client(api_key=self.api_key)
        except Exception as e:
            logger.error(f"Failed to initialize the client: {e}")
            return None

    def generate_moderation_text(self,level:str,message:str):
        if self.client is None:
            return ''
        try:
            response = self.client.models.generate_content(
                model=self.model,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    safety_settings=self.safe_config,
                    response_mime_type=self.response_mime_type
                ),
                contents = f"Generate a response with a {level} tone to moderate this message: {message}"
            )
            try: 
                decode_response = json.loads(response.text.replace('json', '').replace('```','').strip()) if response else None
                if decode_response:
                    logger.info(f'reason: {decode_response.get("reason")}')
                    return decode_response.get('reply')
                else: return ''
            except json.JSONDecodeError as e:
                logger.error(f'Failed to decode: {e}')
                return ''
        except Exception as e:
            logger.error(f'Something went wrong! : {e}') 
            return ''  

