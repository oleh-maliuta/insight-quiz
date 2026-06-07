from google import genai

from app.constants import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)
model_name = 'gemini-2.5-flash'
