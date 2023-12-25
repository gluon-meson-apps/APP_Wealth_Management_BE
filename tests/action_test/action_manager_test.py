from action.action_manager import ActionManager
from action.repository.action_repository import MemoryBasedActionRepository


def test_add_dynamic_action():
    dynamic_action_code = """
class TestAction(DynamicAction):
    def get_name(self) -> str:
        return "test_action"
        
    def run(self, context) -> ActionResponse:
        return ActionResponse(code=200, message="success", answer={}, jump_out_flag=False)
        
    def load_from_config_context(self, config_context: ActionConfigContext):
        pass
    

returned_action=TestAction()
"""
    action_manager = ActionManager(MemoryBasedActionRepository(), None)
    action_manager.add_dynamic_action(dynamic_action_code)
    assert action_manager.action_repository.find_by_name("test_action") is not None
