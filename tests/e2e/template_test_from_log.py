import json


def template_test_for_one_case(logs, test_case):
    expected = logs["expected"]
    actual = logs["actual"]
    for i in range(len(expected)):
        expected_item = {key.split(".")[-1]: value for key, value in expected[i].items()}
        actual_item = {key.split(".")[-1]: value for key, value in actual[i].items()}

        for key in expected_item:
            if 'intent_call_intent' in key and test_case == "e2e":
                assert expected_item[key] == actual_item[key]
            elif 'intent_call_intent' in key and test_case == "intent_call_intent":
                expected_intent = json.loads(expected_item[key])['intent']
                actual_intent = json.loads(actual_item["unit_test_" + key])['intent']
                assert expected_intent == actual_intent, f"round{i+1}: {expected_intent} != {actual_intent}\n check {key}"
            elif 'entity_extractor' in key and test_case == "entity_extractor":
                expected_entity = json.loads(expected_item[key])
                actual_entity = json.loads(actual_item["unit_test_" + key])
                assert expected_entity == actual_entity, f"round{i+1}: {expected_entity} != {actual_entity}\n check {key}"
