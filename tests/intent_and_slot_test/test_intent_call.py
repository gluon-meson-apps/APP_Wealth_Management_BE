from nlu.intent_config import IntentConfig, IntentListConfig
from nlu.llm.intent_call import IntentCall
from prompt_manager.base import BasePromptManager
from tests.intent_and_slot_test.intent_call_prompt import some_system_prompt


def test_construct_system_prompt():
    template = BasePromptManager().load("intent_classification_v2").template
    intent = IntentConfig(name="test_intent", description="the description", action="test_intent", slots=[{
        "name": "test_slot",
        "description": "the description",
        "slotType": "text",
        "optional": False,
    }], business=False, disabled=False)
    intent_call = IntentCall(IntentListConfig([intent]), template, None, None)
    print(intent_call.construct_system_prompt([]))
    assert some_system_prompt == intent_call.construct_system_prompt([])
