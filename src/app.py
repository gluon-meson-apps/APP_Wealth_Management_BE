import os

from action_runner.base import SimpleActionRunner
from conversation_tracker.base import BaseConversationTracker
from dialog_manager.base import BaseDialogManager
from nlu.forms import FormStore
from nlu.mlm.entity import EntityExtractor
from nlu.mlm.intent import IntentClassifier, IntentListConfig
from output_adapter.base import BaseOutputAdapter
from policy_manager.base import BasePolicyManager
from policy_manager.policy import SlotFillingPolicy, RulePolicy
from prompt_manager.base import BasePromptManager
from reasoner.llm_reasoner import LlmReasoner
from fastapi import FastAPI
from uvicorn import run
from pydantic import BaseModel

app = FastAPI()

class MessageInput(BaseModel):
    session_id: str
    user_input: str

def create_reasoner(model_type, action_model_type, intent_config_file_path, prompt_template_folder):
    intent_list_config = IntentListConfig.from_scenes(intent_config_file_path)
    prompt_manager = BasePromptManager(prompt_template_folder)

    classifier = IntentClassifier()
    form_store = FormStore(intent_list_config)
    entity_extractor = EntityExtractor(form_store)

    slot_filling_policy = SlotFillingPolicy(prompt_manager, form_store)
    rule_policy = RulePolicy(prompt_manager, form_store)

    # todo: add priority level to policy
    policy_manager = BasePolicyManager(policies=[slot_filling_policy, rule_policy],
                                       prompt_manager=prompt_manager,
                                       action_model_type=action_model_type)
    return LlmReasoner(classifier, entity_extractor, policy_manager, model_type)


@app.post("/chat/")
def chat(data: MessageInput):
    session_id = data.session_id
    user_input = data.user_input
    model_type = "azure-gpt-3.5"
    action_model_type = "azure-gpt-3.5"

    pwd = os.path.dirname(os.path.abspath(__file__))
    prompt_template_folder = os.path.join(pwd, '.', 'resources', 'prompt_templates')
    intent_config_file_path = os.path.join(pwd, '.', 'resources', 'scenes')

    intent_list_config = IntentListConfig.from_scenes(intent_config_file_path)
    prompt_manager = BasePromptManager(prompt_template_folder)

    classifier = IntentClassifier()
    form_store = FormStore(intent_list_config)
    entity_extractor = EntityExtractor(form_store)

    slot_filling_policy = SlotFillingPolicy(prompt_manager, form_store)
    rule_policy = RulePolicy(prompt_manager, form_store)

    policy_manager = BasePolicyManager(policies=[slot_filling_policy, rule_policy],
                                       prompt_manager=prompt_manager,
                                       action_model_type=action_model_type)
    reasoner = LlmReasoner(classifier, entity_extractor, policy_manager, model_type)
    dialog_manager = BaseDialogManager(BaseConversationTracker(), reasoner, SimpleActionRunner(), BaseOutputAdapter())

    result = dialog_manager.handle_message(user_input, session_id)
    return {"response": result}


def main():
    run(app, host="0.0.0.0", port=7788)

if __name__ == "__main__":
    main()
