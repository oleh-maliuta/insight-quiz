from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from google import genai
from google.genai import types
from pymongo.database import Database
from typing import List
from bson import ObjectId
from datetime import datetime, timezone
import json

from app.schemas.quiz import *
from app.quiz_manager.quiz_controller import take_quiz_controller, finish_quiz_controller, observe_quiz_controller, get_quiz_cards_controller
from app.services.database import get_db
from app.services.oauth import oauth2_scheme
from app.services.ai import client, model_name
from app.utils.db.auth import get_current_user


quiz_manager_router = APIRouter(tags=["Quizzes"])
    
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
                'data': {
                    'quiz_id': str(inserted_quiz_id)
                },
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
    "/take-quiz/{quiz_id}",
    description="Start taking the quiz, create an attempt record, and get access to the sanitized cards."
)
async def take_quiz(
    quiz_id: str,
    token: str = Depends(oauth2_scheme),
    db: Database = Depends(get_db),
):
    return take_quiz_controller(quiz_id, get_current_user(token, db), db)

@quiz_manager_router.post(
    "/finish-quiz",
    description="Finish taking the quiz."
)
async def finish_quiz(
    payload: QuizFinishRequest,
    token: str = Depends(oauth2_scheme),
    db: Database = Depends(get_db),
):
    return finish_quiz_controller(payload=payload, token=token, db=db)

@quiz_manager_router.put(
    "/edit-quiz/{quiz_id}",
    description="Edit the quiz and its cards."
)
async def edit_quiz(
    quiz_id: str,
    quiz_data: QuizCreate,
    token: str = Depends(oauth2_scheme),
    db: Database = Depends(get_db),
):
    try:
        user = get_current_user(token, db)
        if isinstance(user, JSONResponse):
            return user

        try:
            quiz_obj_id = ObjectId(quiz_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid quiz id.")

        quiz = db.quizzes.find_one({"_id": quiz_obj_id})
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz does not exist.")

        if quiz.get('owner_id') != user.id:
            raise HTTPException(status_code=403, detail="User is not the owner of the quiz.")

        if quiz_data.course_id is not None and quiz_data.course_id != quiz.get('course_id'):
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
                if str(course_owner) != str(user.id):
                    raise HTTPException(status_code=403, detail="User is not the owner of the course.")

        current_time = datetime.now(timezone.utc)
        
        quiz_update = {
            "name": quiz_data.name,
            "about": quiz_data.about,
            "attachments": quiz_data.attachments,
            "attempts_allowed": quiz_data.attempts_allowed,
            "course_id": quiz_data.course_id,
            "updated_at": current_time,
        }

        db.quizzes.update_one({"_id": quiz_obj_id}, {"$set": quiz_update})
        db.questions.delete_many({"quiz_id": quiz_obj_id})
        
        questions_to_insert = []
        for q in quiz_data.questions:
            question_document = {
                "quiz_id": quiz_obj_id,
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
            status_code=200,
            content={
                'detail': 'Quiz updated successfully.',
                'data': None,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@quiz_manager_router.delete(
    "/delete-quiz/{quiz_id}",
    description="Delete the quiz."
)
async def delete_quiz(
    quiz_id: str,
    token: str = Depends(oauth2_scheme),
    db: Database = Depends(get_db),
):
    try:
        user = get_current_user(token, db)
        if isinstance(user, JSONResponse):
            return user

        try:
            quiz_obj_id = ObjectId(quiz_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid quiz id.")

        quiz = db.quizzes.find_one({"_id": quiz_obj_id})
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz does not exist.")

        if quiz.get('owner_id') != user.id:
            raise HTTPException(status_code=403, detail="User is not the owner of the quiz.")

        db.questions.delete_many({"quiz_id": quiz_obj_id})
        db.quizzes.delete_one({"_id": quiz_obj_id})

        return JSONResponse(
            status_code=200,
            content={
                'detail': 'Quiz deleted successfully.',
                'data': None,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@quiz_manager_router.get(
    "/observe-quiz/{quiz_id}",
    description="Observe the full quiz and its cards as the author (includes correct answers)."
)
async def observe_quiz(
    quiz_id: str,
    token: str = Depends(oauth2_scheme),
    db: Database = Depends(get_db),
):
    return observe_quiz_controller(quiz_id=quiz_id, token=token, db=db)


@quiz_manager_router.get(
    "/get-quiz-cards/{quiz_id}",
    description="Loads the quiz cards by pages for studying or previewing (sanitized)."
)
async def get_quiz_cards(
    quiz_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Number of cards per page"),
    token: str = Depends(oauth2_scheme),
    db: Database = Depends(get_db),
):
    return get_quiz_cards_controller(quiz_id=quiz_id, page=page, size=size, token=token, db=db)