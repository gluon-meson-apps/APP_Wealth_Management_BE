import os

import pytest

from tests.e2e.fixed.tmp.extraction_from_history import get_construct_chat_message, \
    check_entity_extraction_from_history

os.environ["GLUON_MESON_CONTROL_CENTER_ENDPOINT"] = "http://bj-3090.private.gluon-meson.tech:18000"
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter


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

user_intent = """lc_acceptable"""


@pytest.fixture(scope="session")
async def chat_model():
    print("get_chat_model")
    model = await scenario_model_registry.get_model('llm_entity_extractor')
    return model


async def test_case_1(chat_model):
    chat_history = """user: Hi TB Guru, can we accept LC service requested by BANK OF INDIA in India"""

    response = {"bank entity name": "BANK OF INDIA", "country of bank": "India", "country of service provider": "Singapore"}
    retry_count = 3
    minimal_success_count = 3

    chat_params, _ = get_construct_chat_message(user_intent)(chat_history)
    results, reason = await check_entity_extraction_from_history(chat_model, chat_params, response, [],
                                                                 retry_count, minimal_success_count, params)
    assert results[0] == results[1], reason

async def test_case_2(chat_model):
    chat_history = """Hi TB Guru, can we accept LC service issued by BANK OF INDIA in India"""

    response = {"bank entity name": "BANK OF INDIA", "country of bank": "India", "country of service provider": "Singapore"}
    retry_count = 3
    minimal_success_count = 3

    chat_params, _ = get_construct_chat_message(user_intent)(chat_history)
    results, reason = await check_entity_extraction_from_history(chat_model, chat_params, response, [],
                                                                 retry_count, minimal_success_count, params)
    assert results[0] == results[1], reason


async def test_case_3(chat_model):
    chat_history = """Hi TB Guru, are you able to accept LC service requested by BANK OF INDIA in India"""

    response = {"bank entity name": "BANK OF INDIA", "country of bank": "India", "country of service provider": "Singapore"}
    retry_count = 3
    minimal_success_count = 3

    chat_params, _ = get_construct_chat_message(user_intent)(chat_history)
    results, reason = await check_entity_extraction_from_history(chat_model, chat_params, response, [],
                                                                 retry_count, minimal_success_count, params)
    assert results[0] == results[1], reason


async def test_case_3(chat_model):
    chat_history = """Hi TB Guru, can i accept LC service requested by BANK OF INDIA in India"""

    response = {"bank entity name": "BANK OF INDIA", "country of bank": "India", "country of service provider": "Singapore"}
    retry_count = 3
    minimal_success_count = 3

    chat_params, _ = get_construct_chat_message(user_intent)(chat_history)
    results, reason = await check_entity_extraction_from_history(chat_model, chat_params, response, [],
                                                                 retry_count, minimal_success_count, params)
    assert results[0] == results[1], reason

async def test_case_4(chat_model):
    chat_history = """Hi TB Guru, can HSBC Singapore accept LC service requested by BANK OF INDIA in India"""

    response = {"bank entity name": "BANK OF INDIA", "country of bank": "India", "country of service provider": "Singapore"}
    retry_count = 3
    minimal_success_count = 3

    chat_params, _ = get_construct_chat_message(user_intent)(chat_history)
    results, reason = await check_entity_extraction_from_history(chat_model, chat_params, response, [],
                                                                 retry_count, minimal_success_count, params)
    assert results[0] == results[1], reason

async def test_case_5(chat_model):
    chat_history = """Hi TB Guru, can China Bank accept LC service requested by WELAB BANK LIMITED - Hong Kong"""

    response = {"bank entity name": "WELAB BANK LIMITED", "country of bank": "Hong Kong", "country of service provider": "China"}
    retry_count = 3
    minimal_success_count = 3

    chat_params, _ = get_construct_chat_message(user_intent)(chat_history)
    results, reason = await check_entity_extraction_from_history(chat_model, chat_params, response, [],
                                                                 retry_count, minimal_success_count, params)
    assert results[0] == results[1], reason

async def test_case_6(chat_model):
    chat_history = """Hi TB Guru, can HSBCCNSH accept LC service requested by OSABJPJS"""

    response = {"bic code": "HSBCCNSH", "SWIFT code": "OSABJPJS"}
    retry_count = 3
    minimal_success_count = 3

    chat_params, _ = get_construct_chat_message(user_intent)(chat_history)
    results, reason = await check_entity_extraction_from_history(chat_model, chat_params, response, [],
                                                                 retry_count, minimal_success_count, params)
    assert results[0] == results[1], reason
