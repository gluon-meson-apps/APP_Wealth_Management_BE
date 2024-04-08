from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from loguru import logger

from action.base import Action, ActionResponse, ResponseMessageType, ChatResponseAnswer, GeneralResponse
from third_system.knowledge_base import KnowledgeBase
from third_system.search_entity import SearchParam, SearchItemReference, SearchItem

RETRY_TIMES, SORRY = 1, '抱歉'
FAQ_SCORE_THRESHOLD = 100

summarize_prompt = """
## 角色：语言能力专家。

## 任务：
- 根据聊天记录和用户提问专用词汇数据集合，总结优先级最高的问题，也就是用户最近提的问题。

## 要求：
- 请注意，对话历史后期的问题优先级高于开头的问题。
- 总结的问题需要带着相关的完整的上下文。

## 使用以下格式总结问题：
问题：{摘要问题}

## 聊天记录
{{chat_history}}
"""

chat_prompt = """
## 角色：财富管理AI助手

## 背景：作为财富管理AI助手，你需要理解并回答用户的问题。

## 任务：根据@{聊天历史记录}中的相关信息回答用户提出的的问题。

## 要求：
- 在@{聊天历史记录}中查找与@{用户问题}相关的信息，来回答@{用户问题}。
- 你回复的格式务必如下：
    - 如果历史记录中没有与@{用户问题}相关的信息，请回答：抱歉，没有查询到相关数据，请提供更详细的信息。
    - 如果历史记录中有与@{用户问题}相关的信息，则按照用户要求回答@{用户问题}。
- 以第二人称的形式回答@{用户问题}。

## 用户问题：
{{question}}

## 聊天历史记录：
{{chat_history}}
"""

reply_prompt = """
## 角色：财富管理AI助手

## 背景：We need an AI assistant help Bank institution Private wealth manager who Serve high-end of the market to read research report.

## 任务：根据查询结果回答@{用户问题}。

## 要求：
- 以第二人称的形式回答@{用户问题}：
- 注意你回复的格式应当如下所示：
    - 如果@{用户问题}为空，请回答：抱歉，没有找到相关数据，请提供更详细的信息.
    - 否则总结@{查询结果}来回答@{用户问题}
## 用户问题：
{{question}}

## 查询结果：
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


class ResearchReportNavigatorAction(Action):
    def __init__(self):
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"
        self.knowledge_base = KnowledgeBase()

    def get_name(self) -> str:
        return "research_report_navigator"

    async def search_from_knowledge_base(self, user_input):
        search_param = SearchParam(query=user_input)
        search_response = self.knowledge_base.insurance_search(param=search_param, topic="wealth_management")

        return search_response.page, (search_response.items[0]
                                      if search_response.items and search_response.items[
            0].search__score < FAQ_SCORE_THRESHOLD
                                      else None)

    async def run(self, context) -> ActionResponse:
        logger.info(f"exec action:\n {self.get_name()} ")
        chat_model = await self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)

        history = context.conversation.get_history().format_string()
        question = summarize_question(chat_model, summarize_prompt, history=history)

        result = reply_question(chat_model, chat_prompt, question, history=history)

        retry_times, ex = RETRY_TIMES, None
        while result.startswith(SORRY) and retry_times > 0:
            retry_times -= 1

            page, response = await self.search_from_knowledge_base(context.conversation.current_user_input)
            logger.info(f"search response: {response}")

            references = [
                SearchItem(meta__score=1.0,
                           meta__reference=SearchItemReference(
                               meta__source_type=response.type,
                               meta__source_name=response.field__source,
                               meta__source_page=page,
                               meta__source_content=response.field__text
                           ))
            ]
            result = reply_question(chat_model, reply_prompt, question, query_result=response.field__text)
            logger.info(f'references is {references}')
            answer = ChatResponseAnswer(
                messageType=ResponseMessageType.FORMAT_TEXT,
                content=result,
                intent=context.conversation.current_intent.name,
                references=references
            )
            return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)
