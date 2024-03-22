from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from loguru import logger

from nlu.intent_with_entity import Slot

same_topic_prompt = """## ROLE
you are a helpful assistant

## Tasks
1. estimate if the user changed to a new topic.
2. if the user changed to a new topic, reorganize use's new request combine with the history ON BEHALF OF USER.

## ATTENTION
1. the summary should contains details, someone who don't know the history should be able to understand new request.
2. DON'T MENTION the previous request in the summary.
3. DON'T add or miss any information in the summary.

## CHAT HISTORY
{{chat_history}}

## OUTPUT FORMAT
{
"start_new_topic": true/false,
"new_request": "..." // describe the new request ON BEHALF OF user, for example: I want to.../I'd like to.../Can you help me to.../Hello.../
}"""

more_info_prompt = """## ROLE
you are a helpful assistant

## Tasks
1. The user's last input was missing some necessary information, so you asked the user some questions to obtain this information.
2. Please determine whether user is fill in missing information.

## Description of Missing Information

{{entities}}

## OUTPUT FORMAT
{
"assistant ask for": [...],
"chain of thought": "...", // should start with "let's follow the flow of rule checking and think step by step, 1. check if user reply with full sentence, the result is ... ", end with "so the use is filling(or not filling) the missing information"
"extracted_missing_info": {...}, // the missing information, leave it empty if user is not filling the missing information
"fill in missing information": true/false
}

## flow of rule checking

```python
# Overall rule: Any typo is allowed, as long as the meaning is correct, it should be considered as fill in missing information

# 1. Check if user reply with full sentence
if user_reply == "full sentence":
    # 1.1 Check if user ask a question
    if user_question:
        print("Consider as NOT fill in missing information")

    # 1.2 Check if user request another requirement or say something totally irrelevant
    if user_request_irrelevant:
        print("Consider as NOT fill in missing information")

    # 1.3 Check if user still focus on previous question
    if user_focus_previous_question:
        # Check if user answer the missing information and explicitly mention it's name
        1.3.1
        if user_answer_missing_info:
            print("Consider as fill in missing information")

    print("Consider as not fill in missing information")

# 2
else:
    # 2.1 Check if the name of missing information is explicitly provided by user
    if missing_info_name_provided:
        print("Consider as fill in missing information")
    # 2.2
    else:
        # 2.2.1 Check format of missing information
        if missing_info_format_correct:
            print("Consider as fill in missing information")
        # 2.2.2
        else:
            # 2.2.2.1 Check if meaning is correct just the typo
            if meaning_correct:
                print("Consider as fill in missing information")
            # 2.2.2.2
            else:
                print("Consider as not fill in missing information")
```

here is the example

### chat history
Assistant: what's the country you are currently residing in?
User: New York

### the response
{
"assistant ask for": ["the country of user currently residing in"],
"chain of thought": "let's follow the flow of rule checking and think step by step, 1. Check if user reply with full sentence, 'New York' is not a full sentence,the check result is no. 2.1 Check if the name of missing information is explicitly provided by user, country keyword is not provided,the check result is no, 2.2.1 Check format of missing information is correct, 'New York' is not a country, the result is no, 2.2.2.1 Check if the meaning is correct despite the typo, 'New York' is not a country,the result is no, so the user is not filling in the missing information",
"fill in missing information": False
}

### chat history

User: how many tax I need to pay for the product?
Assistant: what's the country you are currently residing in?
User: how many tax I need to pay for the product in China?

### the response
{
"assistant ask for": ["the country of user currently residing in"],
"chain of thought": "let's follow the flow of rule checking and think step by step, 1. Check if user reply with full sentence, 'how many tax I need to pay for the product in China?' is a full sentence, the result is yes. 1.1 Check if user ask a question, 'how many tax I need to pay for the product in China?' is a question, the result is yes, so the user is not filling in the missing information",
"fill in missing information": False
}

### chat history

User: how many tax I need to pay for the product?
Assistant: what's the country you are currently residing in?
User: I play pingpong in China.

### the response
{
"assistant ask for": ["the country of user currently residing in"],
"chain of thought": "let's follow the flow of rule checking and think step by step, 1. Check if user reply with full sentence, 'I play pingpong in China.' is a full sentence, the result is yes. 1.1 Check if user ask a question, 'I play pingpong in China.' is not a question, the result is no, 1.2 Check if user request another requirement or say something totally irrelevant, 'I play pingpong in China.' is not a request, but it's irrelevant, the result is yes, so the user is not filling in the missing information",
"fill in missing information": False
}

### chat history
User: how many tax I need to pay for the product?
Assistant: what's the country you are currently residing in, and what product you are talking about?

situation 1:
User:China,computer
situation 2:
User:Chna\ncomputer
situation 3:
User:China and conputer

### the response for situation 2
{
"assistant ask for": ["the country of user currently residing in", "the product user is talking about"],
"chain of thought": "let's follow the flow of rule checking and think step by step, 1. Check if user reply with full sentence, 'Chna\ncomputer' is not a full sentence, the result is no. 2.1 Check if the name of missing information is explicitly provided by user, 'the country of user currently residing in' is not explicitly provided, the result is no, 2.2.1 Check format of missing information is correct, 'Chna' and 'computer' are not correct format, the result is no, 2.2.2 Check if meaning is correct just the typo, 'Chna' and 'computer' are correct meaning, the result is yes, so the user is filling in the missing information",
"extracted_missing_info": {"country": "Chna", "product": "computer"},
"fill in missing information": True
}

### chat history

User: how many tax I need to pay for the product?
Assistant: what's the country you are currently residing in, and what product you are talking about?

situation 1:
User: country is China, product is computer
situation 2:
User: country is China\nproduct is computer
situation 3:
User: country is China and product is computer
situation 3:
User: country is C hin a and product is comp uter
situation 4:
User: country is xxx and product is yyy

### the response for situation 4
{
"assistant ask for": ["the country of user currently residing in", "the product user is talking about"],
"chain of thought": "let's follow the flow of rule checking and think step by step, 1. Check if user reply with full sentence, 'country is xxx and product is yyy' is a full sentence, the result is yes. 1.1 Check if user ask a question, 'country is xxx and product is yyy' is not a question, the result is no, 1.2 Check if user request another requirement or say something totally irrelevant, 'country is xxx and product is yyy' is not a request or irrelevant, the result is no, 1.3 Check if user still focus on previous question, 'country is xxx and product is yyy' is still focus on previous question, the result is yes, 1.3.1 Check if user answer the missing information and explicitly mention it's name, 'country' and 'product' are explicitly mentioned, the result is yes, so the user is filling in the missing information",
"extracted_missing_info": {"country": "xxx", "product": "yyy"},
"fill in missing information": True
}

## now let's check

### Chat history

{{history}}

### response

"""


class SameTopicChecker:
    def __init__(self):
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = "same_topic_check"

    def format_history(
        self,
        chat_history: list[dict[str, str]],
    ):
        chat_history_str = ""
        for chat in chat_history:
            i_or_you = "I" if chat["role"] == "user" else "You"
            chat_history_str += f"{i_or_you}: {chat['content']}\n"
        return chat_history_str

    def format_history_with_assistant_and_user(
        self,
        chat_history: list[dict[str, str]],
    ):
        chat_history_str = ""
        for chat in chat_history:
            i_or_you = "User" if chat["role"] == "user" else "Assistant"
            chat_history_str += f"{i_or_you}: {chat['content']}\n"
        return chat_history_str

    async def run(self, history, session_id, prompt, sub_scenario):
        chat_model = await self.scenario_model_registry.get_model(self.scenario_model, session_id)
        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "system", prompt, chat_history=self.format_history_with_assistant_and_user(history)
        )
        chat_message_preparation.log(logger)
        result = (
            await chat_model.achat(
                **chat_message_preparation.to_chat_params(),
                sub_scenario=sub_scenario,
                max_length=256,
                jsonable=True,
            )
        ).get_json_response()
        return result

    async def run_providing_more_information(
        self, history: list[dict[str, str]], session_id: str, prompt: str, sub_scenario: str, unfilled_slot: list[Slot]
    ):
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, session_id)
        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "system", prompt, history=self.format_history_with_assistant_and_user(history), entities=unfilled_slot
        )
        chat_message_preparation.add_message("user", self.format_history(history))
        chat_message_preparation.log(logger)
        result = (
            await chat_model.achat(
                **chat_message_preparation.to_chat_params(),
                sub_scenario=sub_scenario,
                max_length=256,
                jsonable=True,
            )
        ).get_json_response()
        return result

    async def check_same_topic(self, history, session_id):
        result = await self.run(history, session_id, same_topic_prompt, "check_same_topic")
        logger.info(f"same topic check result: {result}")
        if result:
            return result.get("start_new_topic", False), result.get("new_request", "")
        return False, ""

    async def check_is_providing_more_info(
        self, history: list[dict[str, str]], session_id: str, unfilled_slot: list[Slot]
    ):
        # todo: maybe add already provided info can help to improve more.
        result = await self.run_providing_more_information(
            history, session_id, more_info_prompt, "check_if_fill_in_missing_information", unfilled_slot
        )
        logger.info(f"more info check result: {result}")
        if result:
            return result.get("fill in missing information", False), ""
        return False, ""
