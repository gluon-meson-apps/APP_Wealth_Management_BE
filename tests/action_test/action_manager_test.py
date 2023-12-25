import pytest

from action.action_manager import ActionManager
from action.repository.action_repository import MemoryBasedActionRepository


@pytest.fixture
def action_manager():
    return ActionManager(MemoryBasedActionRepository(), None)

def test_add_dynamic_action(action_manager):
    dynamic_action_code = """
class TestAction(DynamicAction):
    def get_name(self) -> str:
        return "test_action"
        
    def run(self, context) -> ActionResponse:
        return ActionResponse(code=200, message="success", answer={}, jump_out_flag=False)
        
    def load_from_config_context(self, config_context: ActionConfigContext):
        pass
    
"""
    action_manager.add_dynamic_action(dynamic_action_code, "TestAction")
    assert action_manager.action_repository.find_by_name("test_action") is not None

def test_should_throw_error_when_import_unavailable_package(action_manager):
    dynamic_action_code = """
from sys import addaudithook
def block_mischief(event,arg):
    if 'WRITE_LOCK' in globals() and ((event=='open' and arg[1]!='r') 
            or event.split('.')[0] in ['subprocess', 'os', 'shutil', 'winreg']): raise IOError('file write forbidden')

addaudithook(block_mischief)
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
