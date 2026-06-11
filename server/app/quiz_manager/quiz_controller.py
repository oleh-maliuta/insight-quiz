from fastapi import HTTPException
from pymongo.database import Database
from fastapi.responses import JSONResponse
from bson import ObjectId
import math
from datetime import datetime, timezone

from app.utils.db.auth import get_current_user

def take_quiz_controller(quiz_id: str, user, db: Database) -> dict:
    """
    Controller for taking a quiz.
    Checks attempt limits, creates a new session, and returns sanitized questions.
    """
    try:
        quiz_obj_id = ObjectId(quiz_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid quiz id.")

    quiz = db.quizzes.find_one({"_id": quiz_obj_id})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz does not exist.")

    attempts_allowed = quiz.get("attempts_allowed", 0)
    if attempts_allowed > 0:
        past_attempts = db.quiz_attempts.count_documents({
            "quiz_id": quiz_obj_id,
            "user_id": user.id
        })
        if past_attempts >= attempts_allowed:
            raise HTTPException(
                status_code=403, 
                detail=f"You have reached the maximum number of attempts ({attempts_allowed}) for this quiz."
            )

    current_time = datetime.now(timezone.utc)
    attempt_doc = {
        "quiz_id": quiz_obj_id,
        "user_id": user.id,
        "started_at": current_time,
        "completed_at": None,
        "status": "in_progress",
        "answers": []
    }
    attempt_result = db.quiz_attempts.insert_one(attempt_doc)

    questions_cursor = db.questions.find({"quiz_id": quiz_obj_id})
    sanitized_questions = []

    for q in questions_cursor:
        sanitized_q = {
            "id": str(q["_id"]),
            "type": q.get("type"),
            "title": q.get("title"),
            "content": q.get("content"),
            "attachments": q.get("attachments")
            # Поле "answer" навмисно ігнорується
        }
        sanitized_questions.append(sanitized_q)

    quiz_metadata = {
        "id": str(quiz["_id"]),
        "name": quiz.get("name"),
        "about": quiz.get("about"),
        "attachments": quiz.get("attachments"),
    }

    return {
        "attempt_id": str(attempt_result.inserted_id),
        "quiz": quiz_metadata,
        "questions": sanitized_questions
    }

def finish_quiz_controller(payload, token: str, db: Database):
    """
    Controller for finishing a quiz attempt.
    Validates the attempt, checks answers, calculates score, and updates the attempt record."""
    try:
        user = get_current_user(token, db)
        if isinstance(user, JSONResponse):
            return user

        try:
            attempt_obj_id = ObjectId(payload.attempt_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid attempt id.")

        attempt = db.quiz_attempts.find_one({"_id": attempt_obj_id})
        if not attempt:
            raise HTTPException(status_code=404, detail="Attempt not found.")

        if attempt.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="This attempt does not belong to the current user.")

        if attempt.get("status") != "in_progress":
            raise HTTPException(status_code=400, detail="This attempt is already completed or invalid.")

        quiz_obj_id = attempt.get("quiz_id")

        questions_cursor = db.questions.find({"quiz_id": quiz_obj_id})
        questions_map = {str(q["_id"]): q for q in questions_cursor}

        correct_answers_count = 0
        total_questions = len(questions_map)
        results_breakdown = []
        user_answers_db = []

        for answer_submit in payload.answers:
            q_id = answer_submit.question_id
            selected = answer_submit.selected_option
            
            user_answers_db.append({
                "question_id": q_id,
                "selected_option": selected
            })

            if q_id in questions_map:
                db_question = questions_map[q_id]
                correct_option = db_question.get("answer", {}).get("correct_option")
                explanation = db_question.get("answer", {}).get("explanation", "")

                is_correct = str(selected).strip() == str(correct_option).strip()
                if is_correct:
                    correct_answers_count += 1

                results_breakdown.append({
                    "question_id": q_id,
                    "is_correct": is_correct,
                    "selected_option": selected,
                    "correct_option": correct_option,
                    "explanation": explanation
                })

        score_percentage = (correct_answers_count / total_questions * 100) if total_questions > 0 else 0
        completed_at = datetime.now(timezone.utc)
        started_at = attempt.get("started_at").replace(tzinfo=timezone.utc) if attempt.get("started_at") else completed_at
        time_spent_seconds = int((completed_at - started_at).total_seconds())

        update_data = {
            "status": "completed",
            "completed_at": completed_at,
            "score_percentage": round(score_percentage, 2),
            "correct_answers": correct_answers_count,
            "total_questions": total_questions,
            "time_spent_seconds": time_spent_seconds,
            "answers": user_answers_db
        }
        
        db.quiz_attempts.update_one(
            {"_id": attempt_obj_id},
            {"$set": update_data}
        )

        return JSONResponse(
            status_code=200,
            content={
                "detail": "Quiz finished successfully.",
                "data": {
                    "attempt_id": payload.attempt_id,
                    "score_percentage": round(score_percentage, 2),
                    "correct_answers": correct_answers_count,
                    "total_questions": total_questions,
                    "time_spent_seconds": time_spent_seconds,
                    "results_breakdown": results_breakdown
                }
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")  

def observe_quiz_controller(quiz_id: str, token: str, db: Database):
    """
    Function to observe a quiz with all its questions and answers.
    Checks permissions and returns detailed quiz data for instructors or admins.
    """
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

        if quiz.get("owner_id") != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="You do not have permission to observe this quiz.")

        questions_cursor = db.questions.find({"quiz_id": quiz_obj_id})
        questions = []
        for q in questions_cursor:
            questions.append({
                "id": str(q["_id"]),
                "type": q.get("type"),
                "title": q.get("title"),
                "content": q.get("content"),
                "attachments": q.get("attachments"),
                "answer": q.get("answer"), 
                "created_at": q.get("created_at").isoformat() if q.get("created_at") else None,
                "updated_at": q.get("updated_at").isoformat() if q.get("updated_at") else None
            })

        quiz_metadata = {
            "id": str(quiz["_id"]),
            "name": quiz.get("name"),
            "about": quiz.get("about"),
            "attachments": quiz.get("attachments"),
            "attempts_allowed": quiz.get("attempts_allowed"),
            "course_id": str(quiz.get("course_id")) if quiz.get("course_id") else None,
            "created_at": quiz.get("created_at").isoformat() if quiz.get("created_at") else None,
            "updated_at": quiz.get("updated_at").isoformat() if quiz.get("updated_at") else None
        }

        return JSONResponse(
            status_code=200,
            content={
                "detail": "Quiz loaded for observation.",
                "data": {
                    "quiz": quiz_metadata,
                    "questions": questions,
                    "total_questions": len(questions)
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

def get_quiz_cards_controller(quiz_id: str, page: int, size: int, token: str, db: Database):
    """
    Function to get quiz cards (questions without answers) with pagination.
    Checks permissions and returns sanitized quiz questions for taking the quiz.
    """
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

        skip = (page - 1) * size
        total_questions = db.questions.count_documents({"quiz_id": quiz_obj_id})
        questions_cursor = db.questions.find({"quiz_id": quiz_obj_id}).skip(skip).limit(size)
        
        sanitized_questions = []
        for q in questions_cursor:
            sanitized_questions.append({
                "id": str(q["_id"]),
                "type": q.get("type"),
                "title": q.get("title"),
                "content": q.get("content"),
                "attachments": q.get("attachments")
            })

        quiz_metadata = {
            "id": str(quiz["_id"]),
            "name": quiz.get("name"),
            "about": quiz.get("about")
        }

        return JSONResponse(
            status_code=200,
            content={
                "detail": "Quiz cards loaded successfully.",
                "data": {
                    "quiz": quiz_metadata,
                    "questions": sanitized_questions,
                    "pagination": {
                        "current_page": page,
                        "page_size": size,
                        "total_items": total_questions,
                        "total_pages": math.ceil(total_questions / size) if size > 0 else 0
                    }
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")