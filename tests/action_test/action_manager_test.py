import pytest

from action.action_manager import ActionManager
from action.context import ActionConfigContext
from action.repository.action_repository import MemoryBasedActionRepository
from nlu.forms import FormStore
from prompt_manager.base import PromptManager


@pytest.fixture
def action_manager():
    return ActionManager(MemoryBasedActionRepository(),
                         ActionConfigContext(prompt_manager=PromptManager(), form_store=FormStore(None)))

def test_add_dynamic_action(action_manager):
    dynamic_action_code = """
class TestAction(DynamicAction):
    def get_name(self) -> str:
        return "test_action"
        
    def run(self, context) -> ActionResponse:
        return ActionResponse(code=200, message="success", answer={}, jump_out_flag=False)
        
    def load_from_config_context(self, config_context: ActionConfigContext):
        self.config_context = config_context
    
"""
    action_manager.add_dynamic_action(dynamic_action_code, "TestAction")
    assert action_manager.action_repository.find_by_name("test_action") is not None
    assert action_manager.action_repository.find_by_name("test_action").config_context == action_manager.action_config_context

def test_should_throw_error_when_import_unavailable_package(action_manager):
    dynamic_action_code = """
class TestAction(DynamicAction):
    def __init__(self):
        import os
        
    def get_name(self) -> str:
        return "test_action"
        
    def run(self, context) -> ActionResponse:
        return ActionResponse(code=200, message="success", answer={}, jump_out_flag=False)
        
    def load_from_config_context(self, config_context: ActionConfigContext):
        pass
    
"""
    action_manager = ActionManager(MemoryBasedActionRepository(), None)
    try:
        action_manager.add_dynamic_action(dynamic_action_code, "TestAction")
    except Exception as e:
        assert str(e) == "__import__ not found"
    try:
        action_manager.action_repository.find_by_name("test_action")
    except Exception as e:
        assert str(e) == "'test_action'"
