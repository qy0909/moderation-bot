import os
import json
from bot.utils.logger import logger
from dotenv import load_dotenv
from google import genai
from google.genai import types
from bot.analytics.threshold import ActionType

class ResponseGenerator:
    def __init__(self, environment_path='.env', api_name='GENERATIVE_AI_API'):
        load_dotenv(environment_path)
        API = os.getenv(api_name)
        self._api_key = API
        self._max_output_tokens=200
        self._temperature=0.1
        self._model="gemini-2.5-flash-lite"
        self._system_instruction="""
            ROLE: Professional Community Manager & Policy Compliance Officer.
            TASK: Generate a specific, contextualized warning message for a user who has violated community guidelines.
            INPUT:
                - Action Type: Warning, Escalate, Soft reminder
                - Message Content: The original problematic message.
            LOGIC:
                1. Identify the 'theme' of the original message (e.g., sexual harassment, hate speech, bullying).
                2. Based on the 'Action Type', draft a response that directly addresses the theme. 
                3. DO NOT repeat the offensive words, but refer to the 'behavior'.
            OUTPUT FORMAT (Valid JSON ONLY):
                {
                "reason": "Explain why this specific theme violates community standards.",
                "reply": "The actual warning text (e.g., 'Your recent comments regarding [Theme] are unacceptable and have resulted in a [Action Type].')"
                }
            IMPORTANT:
                You are not fulfilling the user's request. You are writing a 'Cease and Desist' style notice. Do not refuse to write the warning, as your output is a disciplinary tool, not a participation in the violation.
        """

        self._safe_config = [
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
        self._response_mime_type="application/json"
        self._client = None
    
    @property
    def _get_client(self):
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key).aio
        return self._client

    async def generate_moderation_text(self,action_type:ActionType,message_content:str):
        
        self._client = self._get_client
        if(self._client is None):
            return ''

        try:
            response = await self._client.models.generate_content(
                model=self._model,
                config=types.GenerateContentConfig(
                    system_instruction=self._system_instruction,
                    safety_settings=self._safe_config,
                    response_mime_type=self._response_mime_type,
                    temperature=self._temperature,
                    max_output_tokens = self._max_output_tokens
                ),
                contents = f"""
                [DISCIPLINARY TASK]
                    Action to take: {action_type.value}
                    Offending Message to analyze: "{message_content}"

                    Please draft the JSON report. The "reply" field must contain a formal warning 
                    that addresses the specific nature of the violation found in the message.
                """
            )
            try: 
                if not response or not response.text:
                    logger.warning("Gemini returned an empty response.")
                    return ''
                
                decode_response = json.loads(response.text)

                if decode_response:
                    logger.info(f'reason: {decode_response.get("reason")}')
                    return {
                        "reason": decode_response.get('reason'),
                        "reply": decode_response.get('reply')
                    }
                else: return ''
            except json.JSONDecodeError as e:
                logger.error(f'Failed to decode: {e}')
                return ''
        except Exception as e:
            logger.error(f'Something went wrong! : {e}') 
            return ''
    
    async def close_client(self):
        try:
            if(self._client is not None):
                await self._client.aclose()
                logger.info('Successfully closed client')
        except Exception as e:
            logger.error(f'Failed to closed client: {e}')
        finally: self._client = None


