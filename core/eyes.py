import os
import base64
import openai
from PIL import ImageGrab
from io import BytesIO
from colorama import Fore
from dotenv import load_dotenv

load_dotenv()

class Eyes:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        print(Fore.GREEN + "   ✅ Eyes (GPT-4o Vision) Online")

    def screenshot_to_base64(self):
        img = ImageGrab.grab()
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def look(self, question="What do you see on this screen?"):
        print(Fore.YELLOW + "   [EYES] Capturing screen...")

        try:
            image_b64 = self.screenshot_to_base64()

            # Build a strong prompt that forces GPT-4o to READ the actual content
            system_prompt = (
                "You are J.A.R.V.I.S. analyzing the user's screen. "
                "You MUST read and reference the ACTUAL content visible in the screenshot — "
                "specific variable names, function names, error messages, text, file names, etc. "
                "Do NOT give generic advice. Do NOT say you cannot see the screen. "
                "You are receiving a real screenshot right now — describe and analyze exactly what is in it. "
                "Be concise — your response will be spoken aloud."
            )

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_b64}",
                                    "detail": "high"
                                }
                            },
                            {
                                "type": "text",
                                "text": f"{system_prompt}\n\nUser's question: {question}"
                            }
                        ]
                    }
                ],
                max_tokens=400
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"My visual feed is down, sir. Error: {e}"