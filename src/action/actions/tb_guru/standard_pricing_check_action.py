from loguru import logger

from action.base import Action, ActionResponse, ResponseMessageType, ChatResponseAnswer, GeneralResponse
from llm.self_host import ChatModel
from third_system.search_entity import SearchParam
from third_system.unified_search import UnifiedSearch


prompt = """## Role
you are a chatbot, you need to validate if the pricing offered to the customer is compliant with the standard pricing

## steps

1. check the standard pricing for product.

2. if unit rate lower than what we found from rate card. we replies below

3. if unit rate higher than what we found from rate card, we can recommend the unit price on rate card.

4. reply the comparison result.

## all products info

{all_products}

## product to be check info\n

{product_info}
"""

class StandardPricingCheckAction(Action):
    def __init__(self, model_type: str, chat_model: ChatModel):
        self.unified_search = UnifiedSearch()
        self.model_type = model_type
        self.chat_model = chat_model

    def get_name(self) -> str:
        return 'standard_pricing_check'

    def run(self, context) -> ActionResponse:
        logger.info(f'exec action: {self.get_name()} ')

        # todo: process multi round case
        response = self.unified_search.search(SearchParam(query=context.conversation.current_user_input))
        logger.info(f'search response: {response}')
        all_products = '\n'.join([item.json() for item in response])
        product_info = [dict(
            field=entity.type,
            value=entity.value,
            # description=entity.description
        ) for entity in context.conversation.get_entities()]
        final_prompt = prompt.format(all_products=all_products, product_info=product_info)
        logger.info(f'final prompt: {final_prompt}')
        result = self.chat_model.chat(final_prompt, model_type=self.model_type, max_length=1024)
        logger.info(f'chat result: {result}')

        answer = ChatResponseAnswer(messageType=ResponseMessageType.FORMAT_TEXT, content=result, intent=context.conversation.current_intent.name)
        return GeneralResponse(code=200, message='success', answer=answer, jump_out_flag=False)
