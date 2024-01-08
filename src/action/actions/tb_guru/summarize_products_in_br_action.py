from context import ActionContext

from loguru import logger

from action.base import Action, ActionResponse, ResponseMessageType, ChatResponseAnswer, GeneralResponse
from llm.self_host import ChatModel
from scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from third_system.search_entity import SearchParam
from third_system.unified_search import UnifiedSearch


prompt = """## Role
You are a chatbot, you need to summarize the products referred in the business resolution (br) file \
that I'll provide in the message.

## steps

1. read the business resolution file

2. find what the br file is talking about. 

3. reply with the products referenced in the business resolution file

## Business Resolution File Content

{br_file_content}

## user input

{user_input}

## INSTRUCT

now, answer the question step by step, and reply the final result.

Please reply with a list of products referenced in the business resolution file, without any extra information.

"""

summary_prompt_template = """## Role 
you are a chatbot, you need to summarize the products referred in the business resolution (br) file.

## INSTRUCTION
currently you should summary the result of the conversation, and the result should contains the following information:

{entities}

## chat history

{chat_history}

"""


class SummarizeProductsInBrAction(Action):
    def __init__(self, model_type: str, chat_model: ChatModel) -> None:
        self.unified_search = UnifiedSearch()
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"
        self.model_type = model_type
        self.chat_model = chat_model
        self.default_template = "I don't know how to answer"

    def get_name(self) -> str:
        return 'summarize_products_in_br'

    def run(self, context: ActionContext) -> ActionResponse:
        logger.info(f'exec action: {self.get_name()} ')
        chat_model = self.scenario_model_registry.get_model(self.scenario_model)

        # get the url from entity


        summary_prompt = summary_prompt_template.format(
            entities='\n'.join([entity.json() for entity in context.conversation.get_entities()]),
            chat_history=context.conversation.get_history().format_string())
        result = chat_model.chat(summary_prompt, max_length=1024).response

        # todo: process multi round case
        response = self.unified_search.search(SearchParam(query=result))
        logger.info(f'search response: {response}')
        all_products = '\n'.join([item.model_dump_json() for item in response])
        product_info = [dict(
            field=entity.type,
            value=entity.value,
            # description=entity.description
        ) for entity in context.conversation.get_entities()]
        final_prompt = prompt.format(all_products=all_products, product_info=product_info,
                                     user_input=context.conversation.current_user_input)
        logger.info(f'final prompt: {final_prompt}')
        result = chat_model.chat(final_prompt, max_length=2048).response
        # result = self.chat_model.chat(final_prompt, model_type=self.model_type, max_length=1024)
        logger.info(f'chat result: {result}')

        answer = ChatResponseAnswer(messageType=ResponseMessageType.FORMAT_TEXT, content=result,
                                    intent=context.conversation.current_intent.name)
        return GeneralResponse(code=200, message='success', answer=answer, jump_out_flag=False)
