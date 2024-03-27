
import json

import asyncio

import pytest

from nlu.llm.same_topic_checker import more_info_prompt

scenario = "same_topic_check_check_is_providing_more_info"
use_case = "rma_slot_filling"
params = {
    "top_p": 0.7,
    "jsonable": True,
    "max_length": 512,
    "temperature": 0.0,
    "presence_penalty": 0.0,
    "repetition_penalty": 0.0,
}

def construct_chat_message(user_input, entities):
    from loguru import logger
    from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation

    chat_message_preparation = ChatMessagePreparation()
    first_prompt = more_info_prompt
    chat_message_preparation.add_message(
        'system',
        first_prompt,
        history=user_input,
        entities=entities,
    )

    chat_message_preparation.log(logger)
    chat_params = chat_message_preparation.to_chat_params()
    return chat_params, first_prompt

import os
os.environ["GLUON_MESON_CONTROL_CENTER_ENDPOINT"] = "http://bj-3090.private.gluon-meson.tech:18000"
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter


scenario_model_registry = DefaultScenarioModelRegistryCenter()
chat_model = scenario_model_registry.get_model('same_topic_check')

swift_code = """{ "name": "SWIFT/BIC code", "description": "SWIFT/BIC code of the RMA Counterparty bank, for example BBDAHKHX, UOVBHKHH, PNBPHKHH", "slotType": "text"}"""
country = """{ "name": "country", "description": "the country of the user", "slotType": "text"}"""



@pytest.mark.parametrize("user_input, entities, response, retry_count, minimal_success_count", [
    ("""User: do we have RMA relationship with shanghai bank
Assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of the Shanghai Bank? This code is crucial to check the RMA status. Thank you for your cooperation.
User: I want to know the RMA relationship with shanghai bank.
# """, swift_code, False, 3, 3),
#     ("""User: do we have RMA relationship with shanghai bank
# Assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of the Shanghai Bank? This code is crucial to check the RMA status. Thank you for your cooperation.
# User: 12345
# """, swift_code, False, 3, 3),
#     ("""User: do we have RMA relationship with shanghai bank
# Assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of the Shanghai Bank? This code is crucial to check the RMA status. Thank you for your cooperation.
# User: BOSHCNSH
# """, swift_code, True, 3, 3),
#     ("""User: do we have RMA relationship with shanghai bank
# Assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of the Shanghai Bank? This code is crucial to check the RMA status. Thank you for your cooperation.
# User: do we have RMA relationship with beijing bank and SWIFT/BIC code is BOSHCNSHA
# """, swift_code, False, 10, 8),
#     ("""User: do we have RMA relationship with shanghai bank
# Assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of the Shanghai Bank? This code is crucial to check the RMA status. Thank you for your cooperation.
# User: the SWIFT/BIC code of Shanhai Bank is UOVBHKHH
# """, swift_code, True, 3, 3),
#     ("""User: Please help me what’s the specification I need to follow with br file letterhead
# Assistant: Dear user, to assist you better with the specifications for the BR file letterhead, could you please provide me with the country you are currently residing in? This information is crucial as the requirements may vary based on your location.
# User: 123
# """, country, False, 3, 3),
#     ("""User: Please help me what’s the specification I need to follow with br file letterhead
# Assistant: Dear user, to assist you better with the specifications for the BR file letterhead, could you please provide me with the country you are currently residing in? This information is crucial as the requirements may vary based on your location.
# User: c h i n a
# """, country, True, 3, 3),
#     ("""User: Please help me what’s the specification I need to follow with br file letterhead
# Assistant: Dear user, to assist you better with the specifications for the BR file letterhead, could you please provide me with the country you are currently residing in? This information is crucial as the requirements may vary based on your location.
# User: the country is UOVBHKHH
# """, country, True, 3, 3),
#     ("""User: Please help me what’s the specification I need to follow with br file letterhead
# Assistant: Dear user, to assist you better with the specifications for the BR file letterhead, could you please provide me with the country you are currently residing in? This information is crucial as the requirements may vary based on your location.
# User: I think it should be China
# """, country, True, 3, 3),

])
async def test_same_topic_check_check_is_providing_more_info_unit_test(user_input, entities, response, retry_count, minimal_success_count):

    chat_params, _ = construct_chat_message(user_input, entities)

    results = []
    for i in range(retry_count):
        result = (await chat_model.achat(**chat_params, **params)).get_json_response()
        print(result)
        results.append(result['fill in missing information'] == response)
        rest_try = retry_count - i - 1
        if rest_try + sum(results) < minimal_success_count:
            assert False, f"minimal success count: {minimal_success_count}; max retry: {retry_count}; results: {results}"
        if sum(results) >= minimal_success_count:
            return

    assert sum(results) >= minimal_success_count, f"results: {results}"

# 1. I am currently residing in the United States.
# 2. I prefer not to disclose my current location.
# 3. Can you provide a general guideline for BR file letterhead specifications?
# 4. Why do you need to know my country for the specifications?
# 5. I am from Canada, does that make a difference in the specifications?
# 6. I don't feel comfortable sharing my location, can you still help me with the specifications?
# 7. I am traveling and don't have a fixed location, how can I proceed with the specifications?
# 8. I am not sure why my location is relevant, can you explain?
# 9. I am currently living in Europe, does that affect the specifications?
# 10. I would like to know more about the purpose of the BR file letterhead before providing my location.
# 11. I am not sure if I want to proceed with this request, can we discuss something else?
# 12. I am not comfortable sharing personal information, can we move on to a different topic?
# 13. I am not sure if I trust this platform with my location, can we continue without it?
# 14. I am hesitant to provide personal information, can you still assist me with the specifications?
# 15. I am not sure if I want to continue this conversation, can we talk about something else?
# 16. I am not sure if I want to proceed with this request, can we discuss a different topic?
# 17. I am not comfortable sharing my location, can we move on to a different question?
# 18. I am not sure if I want to continue this discussion, can we talk about a different subject?
# 19. I am not comfortable sharing my location, can you still help me with the specifications?
# 20. I am not sure if I trust this platform with my personal information, can we continue without it?
# 21. I am hesitant to provide my location, can we discuss something else?
# 22. I am not sure if I want to proceed with this request, can we talk about a different topic?
# 23. I am not comfortable sharing personal information, can we move on to a different question?
# 24. I am not sure if I want to continue this conversation, can we discuss a different subject?
# 25. I am not sure if I want to proceed with this request, can we talk about something else?
# 26. I am not comfortable sharing my location, can we move on to a different topic?
# 27. I am not sure if I trust this platform with my location, can we continue without it?



expected = """"""
previous_output = """{ "reason": "The user provided the SWIFT/BIC code of the Shanghai Bank (BOSHCNSH) in response to our request for missing information.", "response_to_requirement": true}"""
