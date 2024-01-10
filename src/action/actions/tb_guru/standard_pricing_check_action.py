import json

from loguru import logger

from action.base import Action, ActionResponse, ResponseMessageType, ChatResponseAnswer, GeneralResponse
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from third_system.search_entity import SearchParam
from third_system.unified_search import UnifiedSearch


prompt = """## Role
you are a chatbot, you need to validate if the pricing offered to the customer is compliant with the standard pricing

## steps

1. check the standard pricing for product.

2. if unit rate lower than what we found from rate card, then reply it's not compliant and answer the user with something like this:

According to the standard pricing of $product in $country, the unit rate should be $currency $unit_rate per transaction. Therefore the proposed unit rate ($currency $offered_unit_rate) is far lower than the standard pricing. It's not compliant with the standard pricing.

3. if unit rate higher than what we found from rate card, we can recommend the unit price on rate card.

4. reply the comparison result.

## all products info

{all_products}

## product to be check info\n

{product_info}

## user input

{user_input}

## INSTRUCT

now, answer the question step by step, and reply the final result.

"""

summary_prompt_template = """## INSTRUCTION
please summarize the chat history

## chat history

{chat_history}

## Result

"""


class StandardPricingCheckAction(Action):
    def __init__(self):
        self.unified_search = UnifiedSearch()
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"

    def get_name(self) -> str:
        return "standard_pricing_check"

    def run(self, context) -> ActionResponse:
        logger.info(f"exec action: {self.get_name()} ")
        chat_model = self.scenario_model_registry.get_model(self.scenario_model)

        entities_without_unit_rate = json.dumps(
            {
                key: value
                for key, value in context.conversation.get_simplified_entities().items()
                if key != "offered unit price"
            }
        )
        summary_prompt = summary_prompt_template.format(chat_history=context.conversation.get_history().format_string())
        logger.info(f"summary_prompt: {summary_prompt}")
        result = chat_model.chat(summary_prompt, max_length=1024).response
        query = (
            result
            + f"\n #extra infos: 1. offered unit rate should not be a query field, 2. fields to be queried: {entities_without_unit_rate} "
        )
        logger.info(f"query: {query}")

        # todo: process multi round case
        response = self.unified_search.search(SearchParam(query=query))
        logger.info(f"search response: {response}")
        all_products = "\n".join([item.json() for item in response])
        product_info = [
            dict(
                field=entity.type,
                value=entity.value,
                # description=entity.description
            )
            for entity in context.conversation.get_entities()
        ]
        final_prompt = prompt.format(
            all_products=all_products, product_info=product_info, user_input=context.conversation.current_user_input
        )
        logger.info(f"final prompt: {final_prompt}")
        result = chat_model.chat(final_prompt, max_length=2048).response
        # result = self.chat_model.chat(final_prompt, model_type=self.model_type, max_length=1024)
        logger.info(f"chat result: {result}")

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT, content=result, intent=context.conversation.current_intent.name
        )
        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)
