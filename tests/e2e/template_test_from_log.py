import json
import traceback

from utils.common import extract_json_from_code_block


def get_dict_only_with_value_not_empty(d):
    return {
        k: v for k, v in d.items() if v
    }

def check_json_result(expected, actual, keys_to_check=None):
    try:
        expected_entity = get_dict_only_with_value_not_empty(extract_json_from_code_block(expected))
        actual_entity = get_dict_only_with_value_not_empty(extract_json_from_code_block(actual))
        if not keys_to_check:
            keys_to_check = expected_entity.keys()
        return all([expected_entity[k] == actual_entity[k] for k in expected_entity if k in keys_to_check])
    except:
        print(traceback.format_exc())
        return False

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
            elif 'intent_call' in key and 'check_same_topic' not in key and test_case == "intent_call_intent":
                if unit_test_key not in actual_item:
                    unit_test_key = unit_test_key.replace('intent_call_intent', 'intent_call')

                expected_entity = expected_item[key]
                actual_entity = actual_item[unit_test_key]
                expected_entity_json = get_dict_only_with_value_not_empty(extract_json_from_code_block(expected_entity))
                actual_entity_json = get_dict_only_with_value_not_empty(extract_json_from_code_block(actual_entity))
                assert check_json_result(expected_entity, actual_entity, ['intent']), f"round{i+1}: {expected_entity_json['intent']} != {actual_entity_json['intent']}\n check {key}"
            elif 'entity_extractor' in key and test_case == "entity_extractor":
                expected_entity = expected_item[key]
                actual_entity = actual_item[unit_test_key]
                assert check_json_result(expected_entity, actual_entity), f"round{i+1}: {expected_entity} != {actual_entity}\n check {key}"
