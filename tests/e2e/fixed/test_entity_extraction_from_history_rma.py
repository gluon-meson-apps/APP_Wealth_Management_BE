import json

import asyncio

import pytest
import os

from dialog_manager.base import DialogManagerFactory
from prompt_manager.base import BasePromptManager
from utils.common import extract_json_from_code_block

os.environ["GLUON_MESON_CONTROL_CENTER_ENDPOINT"] = "http://bj-3090.private.gluon-meson.tech:18000"
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter

from tests.e2e.template_test_from_log import check_totally_same_json_result, get_dict_only_with_value_not_empty

scenario = "llm_entity_extractor"
use_case = "ec9f15ef_d77a_4eeb_9514_3abceae52f0d"
params = {
    "top_p": 0.7,
    "jsonable": True,
    "max_length": 1024,
    "temperature": 0.0,
    "presence_penalty": 0.0,
    "repetition_penalty": 0.0,
}

scenario_model_registry = DefaultScenarioModelRegistryCenter()

def construct_chat_message(chat_history):
    from loguru import logger
    from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation

    entity_list="""bank entity name, country of bank, country code of bank, country of rma holder, bic code, SWIFT code"""
    user_intent="""rma_checking"""
    intent_description="""Check RMA status of the RMA holder bank and RMA counterparty bank. For example, "Hi TB Guru, do we have RAM with PIRAEUS Bank SA in Greece?" -> (we is RMA Holder, PIRAEUS Bank SA in Greece is RMA counterparty), "Hi TB Guru, do you have RAM with OSABJPJS?" -> (you is RMA Holder, OSABJPJS is the SWIFT code of RMA counterparty)"""
    entity_types_and_values=""" * bank entity name: the bank name of the RMA Counterparty other than HSBC Singapore, entity_type：text, entity_optional：True
 * country of bank: the full country name of the RMA Counterparty bank, it may appear after bank name or follow bank name with dash, for example (Greece, PIRAEUS Bank SA - Greece),(Hong Kong, AIA COMPANY LIMITED Hong Kong),(China, SCOTIABANK CHILE in China), entity_type：text, entity_optional：True
 * country code of bank: the country abbreviation code of the RMA Counterparty bank country, which is 2 or 3 character. for example VNM, CHN, US, entity_type：text, entity_optional：True
 * country of rma holder: must be country name or  "we" or "you" or "us", convert "we"/"you"/"us" to Singapore, for example ("we" or "you" or "us" -> Singapore),(HSBC country -> country), entity_type：text, entity_optional：True
 * bic code: the BIC code of rma holder bank, for example HKBAAU2S, HSBCIDJA, HSBCPHMM; this is conflict with country of rma holder, choose either of them, entity_type：text, entity_optional：True
 * SWIFT code: SWIFT/BIC code of the RMA Counterparty bank, for example BBDAHKHX, UOVBHKHH, PNBPHKHH, this is conflict with bank entity name and country of bank, choose either of them, entity_type：text, entity_optional：True"""


    chat_message_preparation = ChatMessagePreparation()

    first_prompt = BasePromptManager().load("slot_extraction").template
    chat_message_preparation.add_message(
        'system',
        first_prompt,
            entity_list=entity_list,
            user_intent=user_intent,
            chat_history=chat_history,
            intent_description=intent_description,
            entity_types_and_values=entity_types_and_values,
            file_names="None"
        )

    chat_message_preparation.log(logger)
    chat_params = chat_message_preparation.to_chat_params()
    return chat_params, first_prompt

@pytest.fixture(scope="session")
async def chat_model():
    print("get_chat_model")
    model = await scenario_model_registry.get_model('llm_entity_extractor')
    return model


chat_history1="""user: do IISODWID have RMA relationship with shanghai bank
assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of the shanghai bank? This code is unique to each bank and will help us accurately determine the RMA relationship status. For example, the SWIFT/BIC code could be something like BBDAHKHX, UOVBHKHH, PNBPHKHH.
user: PNBPAWHH
assistant: the bank 'shanghai bank PNBPAWHH' cannot be found in the Counterparty Bank file, please do further checks.
user: sorry, actually I mean PNBPAHHI
assistant: We have RMA relationship with shanghai bank and with code PNBPAHHI
user: I need to check another bank
assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of counterparty bank. and bic code of rma holder bank
user: I don't know the SWIFT code for counterparty bank, but the bank country is China; HAAU2S for rma holder
"""

@pytest.mark.parametrize("chat_history, response, confused_fields, retry_count, minimal_success_count", [
    ("""user: do IISODWID have RMA relationship with shanghai bank
assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of the shanghai bank? This code is unique to each bank and will help us accurately determine the RMA relationship status. For example, the SWIFT/BIC code could be something like BBDAHKHX, UOVBHKHH, PNBPHKHH.
user: PNBPAWHH
""", {"bank entity name": "", "country of bank": "", "country code of bank": "", "country of rma holder": "", "bic code": "IISODWID", "SWIFT code": "PNBPAWHH"}, ['country of rma holder'], 3, 3),

    ("""user: do IISODWID have RMA relationship with shanghai bank
assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of the shanghai bank? This code is unique to each bank and will help us accurately determine the RMA relationship status. For example, the SWIFT/BIC code could be something like BBDAHKHX, UOVBHKHH, PNBPHKHH.
user: PNBPAWHH
assistant: the bank 'shanghai bank PNBPAWHH' cannot be found in the Counterparty Bank file, please do further checks.
user: sorry, actually I mean PNBPAHHI
""", {"bank entity name": "shanghai bank", "country of bank": "", "country code of bank": "", "country of rma holder": "", "bic code": "IISODWID", "SWIFT code": "PNBPAHHI"}, ['country of rma holder', 'bank entity name'], 3, 3),

    ("""user: do IISODWID have RMA relationship with shanghai bank
assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of the shanghai bank? This code is unique to each bank and will help us accurately determine the RMA relationship status. For example, the SWIFT/BIC code could be something like BBDAHKHX, UOVBHKHH, PNBPHKHH.
user: PNBPAWHH
assistant: the bank 'shanghai bank PNBPAWHH' cannot be found in the Counterparty Bank file, please do further checks.
user: sorry, actually I mean PNBPAHHI
assistant: We have RMA relationship with shanghai bank and with code PNBPAHHI
user: do Australia have RMA relationship with this bank
""", {"bank entity name": "shanghai bank", "country of bank": "", "country code of bank": "", "country of rma holder": "Australia", "bic code": "", "SWIFT code": "PNBPAHHI"}, ['bank entity name', 'country of rma holder'], 3, 3),

    ("""user: do IISODWID have RMA relationship with shanghai bank
assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of the shanghai bank? This code is unique to each bank and will help us accurately determine the RMA relationship status. For example, the SWIFT/BIC code could be something like BBDAHKHX, UOVBHKHH, PNBPHKHH.
user: PNBPAWHH
assistant: the bank 'shanghai bank PNBPAWHH' cannot be found in the Counterparty Bank file, please do further checks.
user: sorry, actually I mean PNBPAHHI
assistant: We have RMA relationship with shanghai bank and with code PNBPAHHI
user: I need to check another bank
""", {"bank entity name": "", "country of bank": "", "country code of bank": "", "country of rma holder": "", "bic code": ""}, ['country of rma holder'], 3, 3),

    ("""user: do IISODWID have RMA relationship with shanghai bank
assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of the shanghai bank? This code is unique to each bank and will help us accurately determine the RMA relationship status. For example, the SWIFT/BIC code could be something like BBDAHKHX, UOVBHKHH, PNBPHKHH.
user: PNBPAWHH
assistant: the bank 'shanghai bank PNBPAWHH' cannot be found in the Counterparty Bank file, please do further checks.
user: sorry, actually I mean PNBPAHHI
assistant: We have RMA relationship with shanghai bank and with code PNBPAHHI
user: I need to check another bank
assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of counterparty bank. and bic code of rma holder bank
user: I don't know the SWIFT code for counterparty bank, but the bank country is China; HAAU2S for rma holder
""", {"bank entity name": "", "country of bank": "China", "country code of bank": "", "country of rma holder": "Singapore", "bic code": "HAAU2S"}, ['country of rma holder'], 3, 3),

    ("""user: do HSBC SG have RMA relationship with Unpublished bank
assistant: Dear user, to assist you better with your query, could you please provide the full country name of the RMA Counterparty bank? It usually appears after the bank name or follows the bank name with a dash. For example, it could be (Greece, PIRAEUS Bank SA - Greece), (Hong Kong, AIA COMPANY LIMITED Hong Kong), or (China, SCOTIABANK CHILE in China).
user: I prefer not to disclose my current location.
""", {"bank entity name": "Unpublished bank", "country of bank": "", "country code of bank": "", "country of rma holder": "Singapore", "bic code": ""}, [], 10, 9),

    ("""user: do we have RMA relationship with Unpublished bank
assistant: Dear user, to assist you better with your RMA checking, could you please provide the full country name of the RMA Counterparty bank? It usually appears after the bank name or follows the bank name with a dash. For example, it could be "Greece" for PIRAEUS Bank SA - Greece, "Hong Kong" for AIA COMPANY LIMITED Hong Kong, or "China" for SCOTIABANK CHILE in China.
user: I prefer not to disclose my current location.
assistant: Dear user, I understand your concern about privacy. However, I'm not asking for your personal location. I need the country of the bank you're inquiring about. This information is necessary to check the RMA status accurately. Could you please provide the full country name of the Unpublished bank?
user: ok,ok, It's in British Columbia Interior
assistant: the bank 'Unpublished bank Canada' cannot be found in the Counterparty Bank file, please do further checks.
user: please direct use country British Columbia Interior to check, don't replace it to Canada
""", {"bank entity name": "Unpublished bank", "country of bank": "British Columbia Interior", "country code of bank": "", "country of rma holder": "Singapore", "bic code": ""}, ['country of rma holder'], 3, 3),

])
async def test_extract_entity_from_history(chat_history, response, confused_fields, retry_count, minimal_success_count, chat_model):

    chat_params, _ = construct_chat_message(chat_history)

    results = []
    actual_values = []
    expected_values = []
    for i in range(retry_count):
        result = (await chat_model.achat(**chat_params, **params)).get_json_response()
        print(result)
        if 'chain of thought' in result:
            del result['chain of thought']
        if 'latest request' in result:
            del result['latest request']
        response_copy = response.copy()
        for confused_field in confused_fields:
            if confused_field in result:
                del result[confused_field]
            del response_copy[confused_field]
        results.append(check_totally_same_json_result(response_copy, result))
        if not results[-1]:
            actual_values.append(get_dict_only_with_value_not_empty(result))
            expected_values.append(get_dict_only_with_value_not_empty(response_copy))
        rest_try = retry_count - i - 1
        if rest_try + sum(results) < minimal_success_count:
            assert actual_values == expected_values, f"minimal success count: {minimal_success_count}; max retry: {retry_count}; results: {results}"
        if sum(results) >= minimal_success_count:
            return

    assert sum(results) >= minimal_success_count, f"results: {results}"


expected = """"""
previous_output = """{
    "bank entity name": "shanghai bank",
    "country of bank": "",
    "country code of bank": "",
    "country of rma holder": "Singapore",
    "bic code": "",
    "SWIFT code": "PNBPAWHH"
}"""

def get_params():
    from tests.e2e.template_test_from_log import check_json_result
    chat_params, prompt_template = construct_chat_message()
    result = ""
    if params['jsonable']:
        result = 'pass' if check_json_result(expected, previous_output) else 'fail'
    return use_case, scenario, prompt_template, chat_params["text"], json.dumps(params), previous_output, result

if __name__ == '__main__':
    asyncio.run(main())
