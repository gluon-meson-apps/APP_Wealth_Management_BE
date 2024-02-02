import json

from utils.utils import extract_json_from_code_block


def get_dict_only_with_value_not_empty(d):
    return {
        k: v for k, v in d.items() if v
    }

def template_test_for_one_case(logs, test_case):
    expected = logs["expected"]
    actual = logs["actual"]
    for i in range(len(expected)):
        expected_item = {key.split(".")[-1]: value for key, value in expected[i].items()}
        actual_item = {key.split(".")[-1]: value for key, value in actual[i].items()}

        for key in expected_item:
            unit_test_key = "unit_test_" + key
            if 'e2e' in key and test_case == "e2e":
                assert expected_item[key] == actual_item[key]
            elif 'intent_call' in key and test_case == "intent_call_intent":
                if unit_test_key not in actual_item:
                    unit_test_key = unit_test_key.replace('intent_call_intent', 'intent_call')
                expected_intent = extract_json_from_code_block(expected_item[key])['intent']
                actual_intent = extract_json_from_code_block(actual_item[unit_test_key])['intent']
                assert expected_intent == actual_intent, f"round{i+1}: {expected_intent} != {actual_intent}\n check {key}"
            elif 'entity_extractor' in key and test_case == "entity_extractor":
                expected_entity = get_dict_only_with_value_not_empty(extract_json_from_code_block(expected_item[key]))
                actual_entity = get_dict_only_with_value_not_empty(extract_json_from_code_block(actual_item[unit_test_key]))
                assert expected_entity == actual_entity, f"round{i+1}: {expected_entity} != {actual_entity}\n check {key}"
