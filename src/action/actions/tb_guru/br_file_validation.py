from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from loguru import logger

from action.base import ActionResponse, ResponseMessageType, ChatResponseAnswer, GeneralResponse
from action.actions.tb_guru.base import TBGuruAction
from action.context import ActionContext
from third_system.search_entity import SearchParam
from utils.common import get_texts_from_search_response

prompt = """## Role
You are a helpful assistant, you need to answer the question from user based on below info.

## business resolution file content
{{br_file_contents}}

## Training document
{{training_doc}}

## user input
{{user_input}}

## instruction
Now, answer the user's question, and reply the result.
"""

rule_in_input_prompt = """## Role
You are a helpful assistant, you need to answer the question from user based on below info. User input contains BR validation rules. flow the following steps , don't mention step in your answer.


## CHAT FLOW
@startuml
start

repeat :For i=1 to #rules;
  :Show:"rule $i";
  :Show:"- Rule Description:" the summary description of the rule;
if (conformed to the rule) then ([conformed])
  :Show:"- Validation Result: Conformed";
else ([not conformed])
  :Show:"- Validation Result: Not Conformed";
endif
if (find related BR file content) then ([found])
  :Show: "- Reference:" related BR file content(must quote from the BR file);
else ([not found])
  :Show:"N/A";
endif
repeat while (next i)
:Show: "Summary:" the overall summary of
the validation result;

:Show: "Summary Table:" Summary in table format: Rule Number, Rule Description, Validation Result, Detailed Reason, Reference;
stop

if (user mention other requests except BR rule validation?) then ([mentioned])
  :Show: Answer user's other requests
;
endif


@enduml
## business resolution file content
{{br_file_contents}}

## user input
{{user_input}}

## instruction

FOLLOW the CHART FLOW to answer the user's question
"""

no_data_prompt = """## Role
You are a helpful assistant, you need to answer the question from user based on below info.

## Training document

## user input
{{user_input}}

## instruction
Ask the user to check their input because you cannot find related content in training document.
"""


class BrFileValidation(TBGuruAction):
    def __init__(self) -> None:
        super().__init__()

    def get_name(self) -> str:
        return "br_file_validation"

    async def run(self, context: ActionContext) -> ActionResponse:
        logger.info(f"exec action: {self.get_name()} ")

        first_file = await self.download_first_processed_file(context)
        if not first_file:
            return GeneralResponse.normal_failed_text_response(
                "No file uploaded, please upload a file and try again.", context.conversation.current_intent.name
            )

        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)

        user_input = context.conversation.current_user_input

        search_res = await self.unified_search.vector_search(SearchParam(query=user_input, size=2), "training_doc")

        br_file_contents = get_texts_from_search_response(first_file)

        chat_message_preparation = ChatMessagePreparation()
        rule_provided = context.conversation.get_entity_by_name("BR validation rules provided")
        if rule_provided and rule_provided.value:
            chat_message_preparation.add_message(
                "system",
                rule_in_input_prompt,
                br_file_contents=br_file_contents,
                user_input=user_input,
            )
        else:
            training_doc = get_texts_from_search_response(search_res[0]) if search_res else ""
            if training_doc:
                chat_message_preparation.add_message(
                    "user",
                    prompt,
                    br_file_contents=br_file_contents,
                    user_input=user_input,
                    training_doc=training_doc,
                )
            else:
                chat_message_preparation.add_message("system", no_data_prompt, user_input=user_input)
                br_file_contents = ""
        chat_message_preparation.log(logger)
        result = (
            await chat_model.achat(
                **chat_message_preparation.to_chat_params(),
                max_length=2048,
                sub_scenario="validation" if br_file_contents else "no_data",
            )
        ).response
        logger.info(f"chat result: {result}")

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content=result,
            intent=context.conversation.current_intent.name,
            references=search_res[0].items if search_res else [],
        )
        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)
