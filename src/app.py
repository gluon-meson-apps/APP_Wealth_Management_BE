import os
from urllib.request import Request

from dotenv import load_dotenv
from starlette.responses import JSONResponse

from action_runner.base import SimpleActionRunner
from conversation_tracker.base import BaseConversationTracker
from dialog_manager.base import BaseDialogManager
from nlu.forms import FormStore
from nlu.mlm.entity import EntityExtractor
from nlu.mlm.intent import IntentClassifier, IntentListConfig
from output_adapter.base import BaseOutputAdapter
from policy_manager.base import BasePolicyManager
from policy_manager.policy import SlotFillingPolicy, AssistantPolicy, IntentConfirmPolicy
from prompt_manager.base import BasePromptManager
from reasoner.llm_reasoner import LlmReasoner
from fastapi import FastAPI
from uvicorn import run
from pydantic import BaseModel

load_dotenv()

app = FastAPI()
dialog_manager = None


@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as err:
        err_msg = f"Error occurred: {err}"
        print(err_msg)
        return JSONResponse(status_code=500, content=err_msg)


class MessageInput(BaseModel):
    session_id: str
    user_input: str


@app.post("/chat/")
def chat(data: MessageInput):
    session_id = data.session_id
    user_input = data.user_input
    result, conversation = dialog_manager.handle_message(user_input, session_id)
    return {"response": result, "conversation": conversation}


def main():
    global dialog_manager
    model_type = "azure-gpt-3.5"
    action_model_type = "azure-gpt-3.5"

    pwd = os.path.dirname(os.path.abspath(__file__))
    prompt_template_folder = os.path.join(pwd, '.', 'resources', 'prompt_templates')
    intent_config_file_path = os.path.join(pwd, '.', 'resources', 'scenes')

    intent_list_config = IntentListConfig.from_scenes(intent_config_file_path)
    prompt_manager = BasePromptManager(prompt_template_folder)

    classifier = IntentClassifier(intent_list_config)
    form_store = FormStore(intent_list_config)
    entity_extractor = EntityExtractor(form_store)

    slot_filling_policy = SlotFillingPolicy(prompt_manager, form_store)
    assitant_policy = AssistantPolicy(prompt_manager, form_store)
    intent_confirm_policy = IntentConfirmPolicy(prompt_manager, form_store)

    policy_manager = BasePolicyManager(policies=[intent_confirm_policy, slot_filling_policy, assitant_policy],
                                       prompt_manager=prompt_manager,
                                       action_model_type=action_model_type)
    reasoner = LlmReasoner(classifier, entity_extractor, policy_manager, model_type)
    dialog_manager = BaseDialogManager(BaseConversationTracker(), reasoner, SimpleActionRunner(), BaseOutputAdapter())

    if os.getenv("LOCAL_MODE"):
        run("app:app", host="0.0.0.0", port=7788, reload=True,
            reload_dirs=os.path.dirname(os.path.abspath(__file__)))
    else:
        run("app:app", host="0.0.0.0", port=7788)


if __name__ == "__main__":
    main()
