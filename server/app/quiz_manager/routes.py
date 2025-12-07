from fastapi import APIRouter
import google.generativeai as genai
from app.constants import GEMINI_API_KEY

quiz_manager_router = APIRouter(tags=["Quizzes"])

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
def generate_quiz(theme, student_level ,number_of_answers, answer_type, number_of_questions = 1):
    # gemini-2.5 model
    genai.configure(api_key = GEMINI_API_KEY)
    model_name = 'gemini-2.5-flash'
    model = genai.GenerativeModel(model_name)
    response = model.generate_content("Напиши '{}' питання на тему '{}', з {} варіантами відповіді типу '{}', для учнів {}.".
                                      format(number_of_questions, theme, number_of_answers, answer_type, student_level))
    return response.text

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