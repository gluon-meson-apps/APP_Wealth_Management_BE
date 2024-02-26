import pytest

from nlu.intent_config import IntentConfig


def intent_with_full_name_of_parent_intent(full_name_of_parent_intent):
    return IntentConfig(
        name="descendant_intent",
        description="descendant_intent_description",
        action="descendant_intent_action",
        slots=[],
        business=False,
        full_name_of_parent_intent=full_name_of_parent_intent,
        disabled=False,
    )

def ancestor_intent_config():
    return IntentConfig(
        name="ancestor",
        description="ancestor_description",
        action="ancestor_action",
        slots=[],
        business=False,
        full_name_of_parent_intent=None,
        disabled=False,
    )

@pytest.mark.parametrize(
    "descendant, ancestor, expected",
    [
        (intent_with_full_name_of_parent_intent("ancestor.l2.l3"), ancestor_intent_config(), True),
        (intent_with_full_name_of_parent_intent("l2.13"), ancestor_intent_config(), False),
        (intent_with_full_name_of_parent_intent(None), ancestor_intent_config(), False),
        (intent_with_full_name_of_parent_intent("ancestor"), ancestor_intent_config(), True),
    ]
)
def test_is_ancestor_of(descendant, ancestor, expected):
    assert ancestor.is_ancestor_of(descendant) == expected
