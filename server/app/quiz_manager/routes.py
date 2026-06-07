from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from pymongo.database import Database
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone
import json

from app.services.database import get_db
from app.services.oauth import oauth2_scheme
from app.services.ai import client, model_name
from app.utils.db.auth import get_current_user


quiz_manager_router = APIRouter(tags=["Quizzes"])


class QuestionCreate(BaseModel):
    type: str = Field(..., description="Question type like 'single_choice' or 'multiple_choice'")
    title: str = Field(..., description="Short title or text of the question")
    content: Optional[str] = Field(None, description="Expanded text or array of answer options")
    attachments: Optional[List[str]] = None
    answer: Dict[str, Any] = Field(..., description="Object with correct answers and explanations")


class QuizCreate(BaseModel):
    course_id: Optional[str] = None
    name: str
    about: Optional[str] = None
    attachments: Optional[List[str]] = None
    attempts_allowed: int = 0
    questions: List[QuestionCreate] = Field(..., description="Масив питань для цього квізу")


@quiz_manager_router.post(
    "/post-quiz",
    description="Post a new quiz along with its questions.",
)
async def post_quiz(
    quiz_data: QuizCreate,
    token: str = Depends(oauth2_scheme),
    db: Database = Depends(get_db),
):
    try:
        user = get_current_user(token, db)
        if isinstance(user, JSONResponse):
            return user

        if user.role not in ("teacher", "admin"):
            raise HTTPException(status_code=403, detail="User must be a teacher or admin to create quizzes.")

        if quiz_data.course_id is not None:
            try:
                course_obj_id = ObjectId(quiz_data.course_id)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid course id.")

            course = db.courses.find_one({"_id": course_obj_id})
            if not course:
                raise HTTPException(status_code=404, detail="Course does not exist.")

            course_owner = course.get('owner_id')
            if isinstance(course_owner, ObjectId):
                if course_owner != user.id:
                    raise HTTPException(status_code=403, detail="User is not the owner of the course.")
            else:
                if str(course_owner) != str(quiz_data.owner_id):
                    raise HTTPException(status_code=403, detail="User is not the owner of the course.")

        current_time = datetime.now(timezone.utc)
        quiz_doc = {
            "owner_id": user.id,
            "course_id": quiz_data.course_id,
            "name": quiz_data.name,
            "about": quiz_data.about,
            "attachments": quiz_data.attachments,
            "attempts_allowed": quiz_data.attempts_allowed,
            "unavailable_at": None,
            "user_permissions": [],
            "created_at": current_time,
            "updated_at": current_time,
        }
        
        result = db.quizzes.insert_one(quiz_doc)
        inserted_quiz_id = result.inserted_id
        
        questions_to_insert = []
        for q in quiz_data.questions:
            question_document = {
                "quiz_id": inserted_quiz_id,
                "type": q.type,
                "title": q.title,
                "content": q.content,
                "attachments": q.attachments,
                "answer": q.answer,
                "created_at": current_time,
                "updated_at": current_time,
            }
            questions_to_insert.append(question_document)
            
        if questions_to_insert:
            db.questions.insert_many(questions_to_insert)
            
        return JSONResponse(
            status_code=201,
            content={
                'detail': 'Quiz created successfully.',
                'data': None,
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@quiz_manager_router.post(
    "/generate-quiz",
    description="Generate a new quiz with AI.",
    response_model=List[QuestionCreate]
)
def generate_quiz(
    theme: str,
    student_level: str,
    number_of_answers: int,
    answer_type: str,
    number_of_questions: int = 1,
    token: str = Depends(oauth2_scheme),
    db: Database = Depends(get_db),
) -> list:
    user = get_current_user(token, db)
    if isinstance(user, JSONResponse):
        return user

    if user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="User must be a teacher or admin to create quizzes.")

    system_instruction = """
    Ти — професійний методист та генератор тестів. 
    Твоє завдання — створювати високоякісні питання для квізів.
    Відповідь повинна бути ВИКЛЮЧНО у форматі валідного масиву JSON, без Markdown-розмітки та блоків коду.
    """

    user_prompt = f"""
    Створи список із {number_of_questions} питань на тему '{theme}'.
    Рівень складності: для учнів рівня "{student_level}".
    Кількість варіантів відповідей: {number_of_answers}.
    Тип варіантів відповідей: {answer_type} (наприклад, single_choice).

    Важливо: JSON має відповідати моделі бази даних. Структура КОЖНОГО об'єкта в масиві має бути такою:
    {{
        "type": "{answer_type}",
        "title": "Текст питання",
        "content": "JSON-рядок масиву варіантів відповідей. Наприклад: '[\"Варіант 1\", \"Варіант 2\", \"Варіант 3\"]'",
        "answer": {{
            "correct_option": "Текст правильного варіанту (має точно збігатися з одним із варіантів у content)",
            "explanation": "Коротке пояснення, чому ця відповідь правильна"
        }}
    }}
    Мова квізу: Українська.
    """

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type='application/json',
                temperature=0.4
            )
        )
        
        quiz_data = json.loads(response.text)
        return quiz_data

    except json.JSONDecodeError as e:
        print(f"JSON Parsing error: {e}. Raw response: {response.text}")
        raise HTTPException(status_code=500, detail="AI returned invalid JSON format.")
    except Exception as e:
        print(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {str(e)}")


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