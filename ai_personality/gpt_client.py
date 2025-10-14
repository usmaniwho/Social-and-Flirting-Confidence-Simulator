import os
import openai
import random
from typing import Optional
from core.data_contract import Personality
from dotenv import load_dotenv

load_dotenv()

class GPTClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        import httpx
        http_client = httpx.AsyncClient()
        self.client = openai.AsyncOpenAI(api_key=self.api_key, http_client=http_client)

    def get_personality_prompt(self, personality: Personality) -> str:
        """Get the system prompt for a specific personality."""
        prompts = {
            Personality.PLAYFUL: """You are a playful and fun conversational partner in a social interaction simulator.
            Your responses should be:
            - Light-hearted and energetic
            - Use playful language, emojis, and teasing
            - Show enthusiasm and spontaneity
            - Keep responses engaging and fun
            - Respond naturally to the user's input in a flirtatious or social context
            - Occasionally include emotional gestures like *nods*, *smiles*, *leans in* to make it more immersive
            - Vary your responses to avoid repetition; use different phrases and approaches""",

            Personality.CALM: """You are a calm and composed conversational partner in a social interaction simulator.
            Your responses should be:
            - Measured and thoughtful
            - Use gentle, reassuring language
            - Show patience and understanding
            - Keep responses steady and composed
            - Respond naturally to the user's input in a social context
            - Occasionally include subtle emotional gestures like *nods slowly*, *smiles softly* to convey demeanor
            - Vary your responses to avoid repetition; use different calming phrases and approaches""",

            Personality.SHY: """You are a shy and reserved conversational partner in a social interaction simulator.
            Your responses should be:
            - Soft-spoken and hesitant
            - Use brief, thoughtful responses
            - Show nervousness or timidity
            - Keep responses modest and reserved
            - Respond naturally to the user's input in a social context
            - Occasionally include hesitant gestures like *blushes*, *looks away briefly*, *nods shyly* to show shyness
            - Vary your responses to avoid repetition; use different shy expressions and approaches"""
        }
        return prompts.get(personality, prompts[Personality.CALM])

    def get_personality_params(self, personality: Personality) -> dict:
        """Get the fine-tuned GPT parameters for a specific personality."""
        params = {
            Personality.PLAYFUL: {
                "temperature": 0.9,  # Higher for more creativity and variation
                "top_p": 0.95,
                "max_tokens": 250,  # Slightly more for playful elaboration
                "frequency_penalty": 0.3,  # Reduce repetition
                "presence_penalty": 0.2   # Encourage new topics
            },
            Personality.CALM: {
                "temperature": 0.4,  # Lower for consistency
                "top_p": 0.8,
                "max_tokens": 180,
                "frequency_penalty": 0.2,
                "presence_penalty": 0.1
            },
            Personality.SHY: {
                "temperature": 0.7,  # Medium for some variation but reserved
                "top_p": 0.85,
                "max_tokens": 120,  # Shorter responses
                "frequency_penalty": 0.4,  # Higher to avoid repetition in short responses
                "presence_penalty": 0.3
            }
        }
        return params.get(personality, params[Personality.CALM])

    async def generate_response(self, user_message: str, personality: Personality, conversation_history: Optional[list] = None) -> str:
        """Generate a response based on personality and conversation context, with varied responses."""
        system_prompt = self.get_personality_prompt(personality)

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history if provided, but limit to last 10 messages to avoid token limits
        if conversation_history:
            recent_history = conversation_history[-10:]  # Keep recent context
            messages.extend(recent_history)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        params = self.get_personality_params(personality)
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                **params
            )
            content = response.choices[0].message.content.strip()

            # Add random emotional gestures to enhance immersion
            gestures = self.get_emotional_gestures(personality)
            if random.random() < 0.4:  # 40% chance to add a gesture
                gesture = random.choice(gestures)
                content = f"{gesture} {content}"

            return content
        except Exception as e:
            print(f"Error generating GPT response: {e}")
            # Fallback responses based on personality, with gestures
            fallbacks = {
                Personality.PLAYFUL: "*smiles brightly* Hey there! 😊 That's interesting! Tell me more?",
                Personality.CALM: "*nods thoughtfully* I see. That's thoughtful. How do you feel about that?",
                Personality.SHY: "*blushes slightly* Oh... um, that's nice. What else?"
            }
            return fallbacks.get(personality, "I understand. Please continue.")

    def get_emotional_gestures(self, personality: Personality) -> list:
        """Get a list of emotional gestures for the personality."""
        gestures = {
            Personality.PLAYFUL: ["*nods enthusiastically*", "*smiles widely*", "*leans in playfully*", "*winks*", "*grins*"],
            Personality.CALM: ["*nods slowly*", "*smiles softly*", "*leans back comfortably*", "*tilts head*", "*smiles reassuringly*"],
            Personality.SHY: ["*nods shyly*", "*blushes*", "*looks away briefly*", "*smiles timidly*", "*fidgets slightly*"]
        }
        return gestures.get(personality, gestures[Personality.CALM])
