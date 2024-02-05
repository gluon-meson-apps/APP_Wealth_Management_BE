import pytest

from nlu.forms import FormStore
from nlu.intent_config import IntentConfig, IntentListConfig
from nlu.intent_with_entity import IntentWithEntity
from policy.slot_filling_policy import SlotFillingPolicy
from tracker.context import ConversationContext


@pytest.fixture
def intent_config():
    return IntentConfig(
        name="test",
        description="test",
        business="test",
        action="test",
        slots=[
            {
                "name": "test",
                "description": "test",
                "slotType": "text",
                "optional": False
            }
        ]
    )


def create_intent_config_with_multiple_slot_name_optional_tuples(slot_name_optional_tuples):
    return IntentConfig(
        name="test",
        description="test",
        business="test",
        action="test",
        slots=[
            {
                "name": slot_name,
                "description": "test",
                "slotType": "text",
                "optional": slot_optional
            }
            for slot_name, slot_optional in slot_name_optional_tuples
        ]
    )


@pytest.fixture
def form_store(intent_config):
    return FormStore(IntentListConfig([intent_config]))


@pytest.fixture
def intent_with_entity(intent_config):
    return IntentWithEntity.model_validate({
        "intent": {
            "name": "test",
            "description": "test",
            "confidence": 1,
        },
        "entities": [
            {
                "type": "test",
                "value": "test",
                "role": "test",
                "confidence": 1
            }
        ],
        "action": "test"
    }
    )

def create_intent_with_entity_by_slot_names(slot_names):
    return IntentWithEntity.model_validate({
        "intent": {
            "name": "test",
            "description": "test",
            "confidence": 1,
        },
        "entities": [
            {
                "type": slot_name,
                "value": "test",
                "role": "test",
                "confidence": 1,
                "possible_slot": {
                    "name": slot_name,
                    "description": "test",
                    "slotType": "text",
                    "optional": False,
                    "confidence": 1,
                }

            }
            for slot_name in slot_names
        ],
        "action": "test"
    }
    )


@pytest.fixture
def conversation_context():
    context = ConversationContext("", "")
    return context


class FakePromptManager:
    def load(self, *args, **kwargs):
        return "test"


@pytest.mark.parametrize("expected_handle, expected_action, form_intent_slots, identified_slot_names", [
    (False, None, [("test", False)], ["test"]),
    (False, None, [("test", True)], ["test"]),
    (False, None, [("test", True)], []),
    (True, "slot_filling", [("test", True), ("test2", False)], ["test"]),
    (True, "slot_filling", [("test", True), ("test2", False)], []),
    (True, "slot_filling", [("test", False)], []),
    (False, None, [], []),
    (False, None, [], ["any"]),
])
def test_return_slot_filling_action_when_mandatory_slot_is_missing_and_no_expression(
        expected_handle, expected_action, form_intent_slots, identified_slot_names, conversation_context):
    slot_filling_policy = SlotFillingPolicy(
        FakePromptManager(),
        FormStore(IntentListConfig([create_intent_config_with_multiple_slot_name_optional_tuples(form_intent_slots)])))
    response = slot_filling_policy.handle(create_intent_with_entity_by_slot_names(identified_slot_names), conversation_context)
    assert response.handled is expected_handle
    if expected_action is None:
        assert response.action is None
    else:
        assert response.action.get_name() == expected_action
