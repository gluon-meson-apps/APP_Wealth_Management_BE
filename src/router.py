from fastapi import APIRouter

from action.controller import action_controller

api_router = APIRouter()
api_router.include_router(
    action_controller.router,
    prefix="/actions",
    tags=["actions"],
    responses={404: {"description": "Not found"}},
)
