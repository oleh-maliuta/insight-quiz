from fastapi import APIRouter

quiz_manager_router = APIRouter(tags=["Quizzes"])

@quiz_manager_router.post(
    "/post-quiz",
    description="Post a new quiz."
)
def post_quiz():
    pass

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