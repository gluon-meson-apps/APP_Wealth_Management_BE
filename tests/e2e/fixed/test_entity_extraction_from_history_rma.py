import os

import pytest

from tests.e2e.fixed.extraction_from_history import get_construct_chat_message, \
    check_entity_extraction_from_history

os.environ["GLUON_MESON_CONTROL_CENTER_ENDPOINT"] = "http://bj-3090.private.gluon-meson.tech:18000"
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter

scenario = "llm_entity_extractor"
use_case = "ec9f15ef_d77a_4eeb_9514_3abceae52f0d"
params = {
    #top_p: 0.95: 100% 0.7: 100%; 0.2: 100% 5min; 0.05: 100% 4m
    #temperature: 2: 5/7 sometimes can't generate valid json, somethings can't generate correct result
    "top_p": 0.7,
    "jsonable": True,
    "max_length": 1024,
    "temperature": 0.0,
    "presence_penalty": 0.0,
    "repetition_penalty": 0.0,
}

scenario_model_registry = DefaultScenarioModelRegistryCenter()

user_intent = """rma_checking"""


@pytest.fixture(scope="session")
async def chat_model():
    print("get_chat_model")
    model = await scenario_model_registry.get_model('llm_entity_extractor')
    return model



async def test_case_1(chat_model):
    chat_history = """user: do IISODWID have RMA relationship with shanghai bank
assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of the shanghai bank? This code is unique to each bank and will help us accurately determine the RMA relationship status. For example, the SWIFT/BIC code could be something like BBDAHKHX, UOVBHKHH, PNBPHKHH.
user: PNBPAWHH
"""
    response = {"bank entity name": "", "country of bank": "", "country code of bank": "", "country of rma holder": "",
                "bic code": "IISODWID", "SWIFT code": "PNBPAWHH"}
    confused_fields = ['country of rma holder']
    retry_count = 3
    minimal_success_count = 3
    chat_params, _ = get_construct_chat_message(user_intent)(chat_history)
    results, reason = await check_entity_extraction_from_history(chat_model, chat_params, response, confused_fields,
                                                                 retry_count, minimal_success_count, params)
    assert results[0] == results[1], reason



async def test_case_2(chat_model):
    chat_history = """user: do IISODWID have RMA relationship with shanghai bank
assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of the shanghai bank? This code is unique to each bank and will help us accurately determine the RMA relationship status. For example, the SWIFT/BIC code could be something like BBDAHKHX, UOVBHKHH, PNBPHKHH.
user: PNBPAWHH
assistant: the bank 'shanghai bank PNBPAWHH' cannot be found in the Counterparty Bank file, please do further checks.
user: sorry, actually I mean PNBPAHHI
""",
    response = {"bank entity name": "shanghai bank", "country of bank": "", "country code of bank": "",
                "country of rma holder": "", "bic code": "IISODWID", "SWIFT code": "PNBPAHHI"}
    confused_fields = ['country of rma holder', 'bank entity name']
    retry_count = 3
    minimal_success_count = 3
    chat_params, _ = get_construct_chat_message(user_intent)(chat_history)
    results, reason = await check_entity_extraction_from_history(chat_model, chat_params, response, confused_fields,
                                                                 retry_count, minimal_success_count, params)
    assert results[0] == results[1], reason



async def test_case_3(chat_model):
    chat_history = """user: do IISODWID have RMA relationship with shanghai bank
assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of the shanghai bank? This code is unique to each bank and will help us accurately determine the RMA relationship status. For example, the SWIFT/BIC code could be something like BBDAHKHX, UOVBHKHH, PNBPHKHH.
user: PNBPAWHH
assistant: the bank 'shanghai bank PNBPAWHH' cannot be found in the Counterparty Bank file, please do further checks.
user: sorry, actually I mean PNBPAHHI
assistant: We have RMA relationship with shanghai bank and with code PNBPAHHI
user: do Australia have RMA relationship with this bank
""",
    response = {"bank entity name": "shanghai bank", "country of bank": "", "country code of bank": "",
                "country of rma holder": "Australia", "bic code": "", "SWIFT code": "PNBPAHHI"}
    confused_fields = ['bank entity name', 'country of rma holder']
    retry_count = 3
    minimal_success_count = 3
    chat_params, _ = get_construct_chat_message(user_intent)(chat_history)
    results, reason = await check_entity_extraction_from_history(chat_model, chat_params, response, confused_fields,
                                                                 retry_count, minimal_success_count, params)
    assert results[0] == results[1], reason



async def test_case_4(chat_model):
    chat_history = """user: do IISODWID have RMA relationship with shanghai bank
assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of the shanghai bank? This code is unique to each bank and will help us accurately determine the RMA relationship status. For example, the SWIFT/BIC code could be something like BBDAHKHX, UOVBHKHH, PNBPHKHH.
user: PNBPAWHH
assistant: the bank 'shanghai bank PNBPAWHH' cannot be found in the Counterparty Bank file, please do further checks.
user: sorry, actually I mean PNBPAHHI
assistant: We have RMA relationship with shanghai bank and with code PNBPAHHI
user: I need to check another bank
""",
    response = {"bank entity name": "", "country of bank": "", "country code of bank": "", "country of rma holder": "",
                "bic code": ""}
    confused_fields = ['country of rma holder']
    retry_count = 3
    minimal_success_count = 3
    chat_params, _ = get_construct_chat_message(user_intent)(chat_history)
    results, reason = await check_entity_extraction_from_history(chat_model, chat_params, response, confused_fields,
                                                                 retry_count, minimal_success_count, params)
    assert results[0] == results[1], reason



async def test_case_5(chat_model):
    chat_history = """user: do IISODWID have RMA relationship with shanghai bank
assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of the shanghai bank? This code is unique to each bank and will help us accurately determine the RMA relationship status. For example, the SWIFT/BIC code could be something like BBDAHKHX, UOVBHKHH, PNBPHKHH.
user: PNBPAWHH
assistant: the bank 'shanghai bank PNBPAWHH' cannot be found in the Counterparty Bank file, please do further checks.
user: sorry, actually I mean PNBPAHHI
assistant: We have RMA relationship with shanghai bank and with code PNBPAHHI
user: I need to check another bank
assistant: Dear user, to assist you better with your query, could you please provide the SWIFT/BIC code of counterparty bank. and bic code of rma holder bank
user: I don't know the SWIFT code for counterparty bank, but the bank country is China; HAAU2S for rma holder
""",
    response = {"bank entity name": "", "country of bank": "China", "country code of bank": "",
                "country of rma holder": "Singapore", "bic code": "HAAU2S"}
    confused_fields = ['country of rma holder']
    retry_count = 3
    minimal_success_count = 3
    chat_params, _ = get_construct_chat_message(user_intent)(chat_history)
    results, reason = await check_entity_extraction_from_history(chat_model, chat_params, response, confused_fields,
                                                                 retry_count, minimal_success_count, params)
    assert results[0] == results[1], reason



async def test_case_6(chat_model):
    chat_history = """user: do HSBC SG have RMA relationship with Unpublished bank
assistant: Dear user, to assist you better with your query, could you please provide the full country name of the RMA Counterparty bank? It usually appears after the bank name or follows the bank name with a dash. For example, it could be (Greece, PIRAEUS Bank SA - Greece), (Hong Kong, AIA COMPANY LIMITED Hong Kong), or (China, SCOTIABANK CHILE in China).
user: I prefer not to disclose my current location.
""",
    response = {"bank entity name": "Unpublished bank", "country of bank": "", "country code of bank": "",
                "country of rma holder": "Singapore", "bic code": ""}
    confused_fields = []
    retry_count = 10
    minimal_success_count = 9
    chat_params, _ = get_construct_chat_message(user_intent)(chat_history)
    results, reason = await check_entity_extraction_from_history(chat_model, chat_params, response, confused_fields,
                                                                 retry_count, minimal_success_count, params)
    assert results[0] == results[1], reason



async def test_case_7(chat_model):
    chat_history = """user: do we have RMA relationship with Unpublished bank
assistant: Dear user, to assist you better with your RMA checking, could you please provide the full country name of the RMA Counterparty bank? It usually appears after the bank name or follows the bank name with a dash. For example, it could be "Greece" for PIRAEUS Bank SA - Greece, "Hong Kong" for AIA COMPANY LIMITED Hong Kong, or "China" for SCOTIABANK CHILE in China.
user: I prefer not to disclose my current location.
assistant: Dear user, I understand your concern about privacy. However, I'm not asking for your personal location. I need the country of the bank you're inquiring about. This information is necessary to check the RMA status accurately. Could you please provide the full country name of the Unpublished bank?
user: ok,ok, It's in British Columbia Interior
assistant: the bank 'Unpublished bank Canada' cannot be found in the Counterparty Bank file, please do further checks.
user: please direct use country British Columbia Interior to check, don't replace it to Canada
""",
    response = {"bank entity name": "Unpublished bank", "country of bank": "British Columbia Interior",
                "country code of bank": "", "country of rma holder": "Singapore", "bic code": ""}
    confused_fields = ['country of rma holder']
    retry_count = 3
    minimal_success_count = 3
    chat_params, _ = get_construct_chat_message(user_intent)(chat_history)
    results, reason = await check_entity_extraction_from_history(chat_model, chat_params, response, confused_fields,
                                                                 retry_count, minimal_success_count, params)
    assert results[0] == results[1], reason
