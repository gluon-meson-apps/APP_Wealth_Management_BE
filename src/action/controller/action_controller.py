from fastapi import APIRouter
from fastapi import status

from action.action_manager import ActionManager
from action.controller.command.create_action import CreateActionCommand
from action.controller.response.create_action import CreateActionResponse
from action.repository.action_repository import action_repository

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_application(
        command: CreateActionCommand,
) -> CreateActionResponse:
    # todo: add action Context
    action_manager = ActionManager(action_repository, None)
    action_manager.add_dynamic_action(command.action_code, command.class_name)
    return CreateActionResponse(**command.dict())

