from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from loguru import logger

from action.base import Action, ActionResponse, ResponseMessageType, ChatResponseAnswer, GeneralResponse
from third_system.knowledge_base import KnowledgeBase
from third_system.search_entity import SearchParam, SearchItemReference, SearchItem, SearchParamFilter

SORRY, NUM_K = 'Sorry', 12

summarize_prompt = """
## Role: Language Capability Expert

## Task:
- Summarize the highest priority question based on the chat history and questions posed by the user, i.e., the most recent question raised by the user.

## Requirements:
- Please note that questions raised later in the conversation have higher priority than those raised earlier.
- The summarized question should include relevant and complete context.

## Use the following format to summarize the question:
Question: [Your Summary Question]

## Chat History
{{chat_history}}
"""

chat_prompt = """
## Role: Wealth Management AI Assistant

## Background: As a Wealth Management AI Assistant, you need to understand and respond to user questions.

## Task: Answer user questions based on relevant information in the chat history.

## Requirements:
- Search for information related to the user's question in the chat history to respond to the user's query.
- Your response format must be as follows:
    - If there is no information related to the user's question in the chat history, please respond: "Sorry, no relevant data found. Please provide more details."
    - If there is information related to the user's question in the chat history, respond to the user's question as per their request.
- Respond to user questions in the second person form.

## User Question:
{{question}}

## Chat History:
{{chat_history}}
"""

reply_prompt = """
## Role: Wealth Management AI Assistant

## Background: We need an AI assistant to help the Bank institution's Private Wealth Manager who serves the high-end market to read research reports.

## Task: Respond to user questions based on the query results.

## Requirements:
- Respond to user questions in the second person form.
- Ensure your response is closely related to the question and the search results.
- Ensure your response follows the format below:
    - If the user question is empty, please respond: "Sorry, no relevant data found. Please provide more details."
    - Otherwise, summarize the query results to answer the user's question.
    - If query results are scattered, provide a detailed and accurate answer by extracting relevant information as much as possible.
    - If query results are complex with different dimensions, categorize the answer from multiple perspectives and list them.
    - If query results is empty, please respond: "Sorry, no relevant data found. Please provide more details."
    
## User Question:
{{question}}

## Query Results:
{{query_result}}
"""


def summarize_question(chat_model, prompt, history):
    chat_message_preparation = ChatMessagePreparation()
    chat_message_preparation.add_message(
        "system",
        prompt,
        chat_history=history
    )
    chat_message_preparation.log(logger)
    summarized_question = chat_model.chat(**chat_message_preparation.to_chat_params(), max_length=2048).response
    logger.info(f"summarized_question:\n {summarized_question}")
    return summarized_question


def reply_question(chat_model, prompt, question, history=None, query_result=None):
    chat_message_preparation = ChatMessagePreparation()
    chat_message_preparation.add_message(
        "user",
        prompt,
        question=question,
        chat_history=history,
        query_result=query_result
    )
    chat_message_preparation.log(logger)
    result = chat_model.chat(**chat_message_preparation.to_chat_params(), max_length=2048).response
    logger.info(f"chat result:\n {result}")
    return result


class ResearchReportInquiryAction(Action):
    def __init__(self):
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"
        self.knowledge_base = KnowledgeBase()

    @staticmethod
    def form_filter_with_entities(entities: dict) -> list[SearchParamFilter]:
        filter_query_list = []
        if "topic" in entities:
            filter_query_list.append(SearchParamFilter(
                field="topic",
                op="like",
                value=f"\"{entities['topic']}%\""
            ))

        return filter_query_list

    def get_name(self) -> str:
        return "research_report_inquiry"

    async def search_from_knowledge_base(self, user_input, num_k):
        search_param = SearchParam(
            query=user_input,
            k=num_k
        )
        search_response = self.knowledge_base.insurance_search(param=search_param, topic="wealth_management")
        return search_response.items

    async def run(self, context) -> ActionResponse:
        logger.info(f"exec action:\n {self.get_name()} ")
        chat_model = await self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)

        question = context.conversation.current_user_input
        history = context.conversation.get_history().format_string()

        result, references = reply_question(chat_model, chat_prompt, question, history=history), None

        if result.startswith(SORRY):
            response = await self.search_from_knowledge_base(context.conversation.current_user_input, NUM_K)
            logger.info(f"search response: {response}")

            search_results = {}

            for index, item in enumerate(response):
                reference_key = f"reference_{index}"
                search_results[reference_key] = item.field__text

            references = [
                SearchItem(meta__score=response[0].search__score,
                           meta__reference=SearchItemReference(
                               meta__source_type=response[0].type,
                               meta__source_name=response[0].field__source,
                               meta__source_content=search_results
                           ))
            ] if response else None
            result = reply_question(chat_model, reply_prompt, question, query_result=search_results)

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content=result,
            intent=context.conversation.current_intent.name,
            references=references
        )
        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)