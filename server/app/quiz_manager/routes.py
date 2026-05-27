from fastapi import APIRouter
from google import genai
from google.genai import types
from app.constants import GEMINI_API_KEY
import json

quiz_manager_router = APIRouter(tags=["Quizzes"])
client = genai.Client(api_key=GEMINI_API_KEY)
model_name = 'gemini-2.5-flash' # Gemini AI model

@quiz_manager_router.post(
    "/post-quiz",
    description="Post a new quiz."
)
def post_quiz():
    pass

@quiz_manager_router.post(
    "/generate-quiz",
    description="Generate a new quiz with AI."
)
def generate_quiz(theme: str, student_level: str, number_of_answers: int, answer_type: str, number_of_questions: int = 1) -> list:
    """
    Генерує квіз у форматі JSON.
    """
    
    # 1. Instruction for the AI model
    system_instruction = """
    Ти — професійний методист та генератор тестів. 
    Твоє завдання — створювати високоякісні питання для квізів.
    Відповідь повинна бути ВИКЛЮЧНО у форматі JSON.
    """

    # 2. Detailed user prompt
    user_prompt = f"""
    Створи список із {number_of_questions} питань на тему '{theme}'.
    Рівень складності: для учнів {student_level}.
    Кількість варіантів відповідей: {number_of_answers}.
    Тип варіантів відповідей: {answer_type}.

    Важливо:
    1. Познач правильну відповідь.
    2. Додай коротке пояснення, чому ця відповідь правильна (поле 'explanation').
    3. JSON має виглядати так:
    [
        {{
            "question": "Текст питання",
            "options": ["Варіант 1", "Варіант 2", ...],
            "correct_answer_index": 0,  // Індекс правильної відповіді в масиві options (0, 1, 2...)
            "explanation": "Пояснення..."
        }}
    ]
    Мова квізу: Українська (або відповідно до теми).
    """

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type='application/json',
            )
        )
        
        # 4. Parsing JSON
        quiz_data = json.loads(response.text)
        return quiz_data

    except Exception as e:
        print(f"Generation error: {e}")
        return []

@quiz_manager_router.post(
    "/take-quiz",
    description="Start taking the quiz and get the access to the cards."
)
def take_quiz():
    pass

@quiz_manager_router.post(
    "/finish-quiz",
    description="Finish taking the quiz."
)
def finish_quiz():
    pass

@quiz_manager_router.put(
    "/edit-quiz",
    description="Edit the quiz and its cards."
)
def edit_quiz():
    pass

@quiz_manager_router.delete(
    "/delete-quiz",
    description="Delete the quiz."
)
def delete_quiz():
    pass

@quiz_manager_router.get(
    "/observe-quiz",
    description="Observe the quiz and its cards as the author."
)
def observe_quiz():
    pass

@quiz_manager_router.get(
    "/get-quiz-cards",
    description="Loads the quiz cards by pages."
)
def get_quiz_cards():
    pass