import unittest

import pytest

from nlu.llm.intent import LLMIntentClassifier


@pytest.fixture
def same_intent_examples():
    return [{'intent': '{"top_3_ordered_intent_list": ["br_extension_qa", "other1", "other2"], "intent": "br_extension_qa", "confidence": 1.0}', 'example': 'Hi TB guru, Please help me what’s the specification I need to follow on the Australia BR supporting documents LETTERHEAD', 'score': 0.9302552938461304}, {'intent': '{"top_3_ordered_intent_list": ["br_extension_qa", "other1", "other2"], "intent": "br_extension_qa", "confidence": 1.0}', 'example': 'Hi TB guru, Could you please help me check the Australia BR supporting document requirement for New Authorised Signatory', 'score': 0.8605368733406067}, {'intent': '{"top_3_ordered_intent_list": ["br_extension_qa", "other1", "other2"], "intent": "br_extension_qa", "confidence": 1.0}', 'example': 'Hi TB guru, Please provide the sample attachments of the BR documents ID/Passport Copies', 'score': 0.8460354804992676}]

@pytest.fixture
def different_intent_examples():
    return [{'intent': '{"top_3_ordered_intent_list": ["br_extension_qa", "other1", "other2"], "intent": "br_extension_qa", "confidence": 1.0}', 'example': 'Hi TB guru, Please help me what’s the specification I need to follow on the Australia BR supporting documents LETTERHEAD', 'score': 0.9302552938461304}, {'intent': '{"top_3_ordered_intent_list": ["br_file_qa", "other1", "other2"], "intent": "other1", "confidence": 1.0}', 'example': 'Hi TB guru, Could you please help me check the Australia BR supporting document requirement for New Authorised Signatory', 'score': 0.8605368733406067}, {'intent': '{"top_3_ordered_intent_list": ["br_extension_qa", "other1", "other2"], "intent": "other2", "confidence": 1.0}', 'example': 'Hi TB guru, Please provide the sample attachments of the BR documents ID/Passport Copies', 'score': 0.8460354804992676}]

def test_get_intent_if_all_examples_are_from_same_intent(same_intent_examples):
    result = LLMIntentClassifier.get_same_intent(same_intent_examples)
    assert result == "br_extension_qa"

def test_get_intent_if_all_examples_are_from_different_intent(different_intent_examples):
    result = LLMIntentClassifier.get_same_intent(different_intent_examples)
    assert result == None


class TestGetMappedIntentOfCurrentLayer(unittest.TestCase):
    def test_get_mapped_intent_with_matching_parent_intent(self):
        intent_example = {
            "parent_intent": "parent_intent_of_current_layer",
            "intent": '{"intent": "mapped_intent"}'
        }
        parent_intent_of_current_layer = "parent_intent_of_current_layer"

        mapped_intent = LLMIntentClassifier.get_mapped_intent_of_current_layer(intent_example, parent_intent_of_current_layer)

        self.assertEqual(mapped_intent, "mapped_intent")

    def test_get_mapped_intent_with_non_matching_parent_intent(self):
        intent_example = {
            "parent_intent": "rma_qa.lc_advising",
            "intent": '{"intent": "rma_check"}'
        }
        parent_intent_of_current_layer = "rma_qa"

        mapped_intent = LLMIntentClassifier.get_mapped_intent_of_current_layer(intent_example, parent_intent_of_current_layer)

        self.assertEqual(mapped_intent, "lc_advising")

    def test_get_mapped_intent_with_empty_parent_intent_of_current_layer(self):
        intent_example = {
            "parent_intent": "parent_intent_of_current_layer.child_intent",
            "intent": '{"intent": "mapped_intent"}'
        }
        parent_intent_of_current_layer = None

        mapped_intent = LLMIntentClassifier.get_mapped_intent_of_current_layer(intent_example, parent_intent_of_current_layer)

        self.assertEqual(mapped_intent, "parent_intent_of_current_layer")

if __name__ == '__main__':
    unittest.main()
