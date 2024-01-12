import json
from typing import List


from nlu.base import EntityExtractor
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from tracker.context import ConversationContext
from gluon_meson_sdk.models.chat_model import ChatModel
from loguru import logger
from nlu.forms import FormStore, Form
from nlu.intent_with_entity import Entity
from prompt_manager.base import PromptManager

system_template = """
## Role & Task
你是一个聊天机器人，你需要根据"User Intent"和"Chat History"，
结合提供的"Entities Types & Description"，提取出相应的实体。
如果没有找到对应的实体，输出空字符串，数值型的实体，需要输出的是用户明确表示的具体数值。

## Output Format
重点关注必选的实体，返回格式必须符合yaml格式，下面是一个返回的例子：
```yaml
Entity_1: $Value_1
Entity_n: $Value_n
```
"""


class LLMEntityExtractor(EntityExtractor):
    def __init__(
        self,
        form_store: FormStore,
        chat_model: ChatModel,
        model_type: str,
        prompt_manager: PromptManager,
    ):
        self.form_store = form_store
        self.model = chat_model
        self.model_type = model_type
        self.prompt_manager = prompt_manager
        self.slot_extraction_prompt = prompt_manager.load("slot_extraction")
        self.examples = self.prepare_examples()
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = "llm_entity_extractor"

    def construct_system_prompt(self, conversation_context: ConversationContext, slots: str, intent):
        return self.slot_extraction_prompt.format_jinja(
            user_intent=intent.name,
            chat_history=conversation_context.get_history().format_string(),
            entity_types_and_values=slots,
        )

    def construct_messages(
        self, user_input, intent, form: Form, conversation_context: ConversationContext
    ) -> List[str]:
        final_user_message = user_input
        history = [
            ("system", self.construct_system_prompt(conversation_context, form.get_available_slots_str(), intent))
        ]
        for example in self.examples:
            history.append(("user", example[0]))
            history.append(("assistant", example[1]))
        return final_user_message, history

    def prepare_examples(self):
        examples = [
            (
                "help me to turn on the light in the living room",
                """{ "position": "living room", "operation": "turn on", "object": "light", "operation_value": "on" }""",
            ),
            (
                "turn to 50% brightness",
                """{ "position": "living room", "operation": "turn on", "object": "light", "operation_value": "0.5" }""",
            ),
        ]
        return examples

    def extract_entity(self, conversation_context: ConversationContext) -> List[Entity]:
        user_input = conversation_context.current_user_input
        intent = conversation_context.current_intent
        form = self.form_store.get_form_from_intent(intent)
        if not form:
            logger.debug(f"this intent [{intent.name}] does not need to extract entity")
            return []
        prompt, history = self.construct_messages(user_input, intent, form, conversation_context)
        logger.debug(prompt)
        logger.debug(history)
        chat_model = self.scenario_model_registry.get_model(self.scenario_model)
        response = chat_model.chat(prompt, history=history, max_length=1024)
        logger.debug(response.response)
        if response is None or response.response == "None":
            return []
        entities = json.loads(response.response)
        slot_name_to_slot = {slot.name: slot for slot in form.slots}
        if entities:
            entity_list = list(
                filter(
                    lambda tup: tup[0] in slot_name_to_slot
                    and tup[1] is not None
                    and (isinstance(tup[1], int) or len(str(tup[1])) > 0),
                    list(entities.items()),
                )
            )
        else:
            entity_list = []

        def get_slot(name, value):
            if slot_name_to_slot:
                if name in slot_name_to_slot:
                    slot = slot_name_to_slot[name].copy(update={"value": value})
                    slot.confidence = 1
                    return slot
            return None

        return [Entity(type=name, value=value, possible_slot=get_slot(name, value)) for name, value in entity_list]
