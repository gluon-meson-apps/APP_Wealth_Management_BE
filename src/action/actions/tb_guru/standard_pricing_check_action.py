from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from loguru import logger

from action.base import ActionResponse, ResponseMessageType, ChatResponseAnswer, GeneralResponse
from action.actions.tb_guru.base import TBGuruAction
from third_system.search_entity import SearchParam
from utils.action_helper import format_entities_for_search

prompt = """## Role
you are a chatbot, you need to validate if the pricing offered to the customer is compliant with the standard pricing

## steps

1. check the standard pricing for product.

2. if unit rate lower than what we found from rate card, then reply it's not compliant and answer the user with something like this:

According to the standard pricing of $product in $country, the unit rate should be $currency $unit_rate per transaction. Therefore the proposed unit rate ($currency $offered_unit_rate) is far lower than the standard pricing. It's not compliant with the standard pricing.

3. if unit rate higher than what we found from rate card, we can recommend the unit price on rate card.

4. reply the comparison result.

## all products info

{{all_products}}

## product to be check info\n

{{product_info}}

## chat history

{{chat_history}}

## INSTRUCT

now, answer the question step by step, and reply the final result.

"""

summary_prompt_template = """## INSTRUCTION
please summarize the chat history

## chat history

{{chat_history}}

## Result

"""


class StandardPricingCheckAction(TBGuruAction):
    def __init__(self):
        super().__init__()

    def get_name(self) -> str:
        return "standard_pricing_check"

    async def run(self, context) -> ActionResponse:
        logger.info(f"exec action: {self.get_name()} ")
        chat_model = await self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)

        entities_without_unit_rate = format_entities_for_search(context.conversation, ["offered unit price"])
        history = context.conversation.get_history().format_string({"user": "human"})

        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message("user", summary_prompt_template, chat_history=history)
        chat_message_preparation.log(logger)

        result = (
            await chat_model.achat(**chat_message_preparation.to_chat_params(), max_length=1024, sub_scenario="summary")
        ).response
        query = f"""## User input:
{result}

## ATTENTION
1. offered unit rate should not be a query field
2. fields to be queried: {entities_without_unit_rate}"""
        logger.info(f"query: {query}")

        # todo: process multi round case
        response = await self.unified_search.search(SearchParam(query=query), context.conversation.session_id)
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

        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "user", prompt, all_products=all_products, product_info=product_info, chat_history=history
        )
        chat_message_preparation.log(logger)

        result = (await chat_model.achat(**chat_message_preparation.to_chat_params(), max_length=2048)).response
        logger.info(f"chat result: {result}")

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT, content=result, intent=context.conversation.current_intent.name
        )
        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)
