from nlu.forms import FormStore
from nlu.intent_config import IntentListConfig
from nlu.intent_with_entity import Intent
from nlu.llm.entity import LLMEntityExtractor
from prompt_manager.base import BasePromptManager
from resources.util import get_resources
from tests.e2e.template_test_from_log import check_totally_same_json_result, get_dict_only_with_value_not_empty


def get_construct_chat_message(user_intent):
    def construct_chat_message(chat_history):
        from loguru import logger
        from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation

        chat_message_preparation = ChatMessagePreparation()
        intent_config_file_path = get_resources("scenes")
        form = FormStore(IntentListConfig.from_scenes(intent_config_file_path)).get_form_from_intent(Intent(name=user_intent))

        first_prompt = BasePromptManager().load("slot_extraction").template
        LLMEntityExtractor.construct_messages_cls(
            first_prompt,
            user_intent,
            form=form,
            chat_history=chat_history,
            file_names="None",
            preparation=chat_message_preparation
        )

        chat_message_preparation.log(logger)
        chat_params = chat_message_preparation.to_chat_params()
        return chat_params, first_prompt
    return construct_chat_message

async def check_entity_extraction_from_history(chat_model, chat_params, response, confused_fields, retry_count, minimal_success_count, params):
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
            return (actual_values, expected_values), f"minimal success count: {minimal_success_count}; max retry: {retry_count}; results: {results}"
        if sum(results) >= minimal_success_count:
            return (True, True), None

    if sum(results) >= minimal_success_count:
        return (True, True), None
    return (True, False), f"results: {results}"
