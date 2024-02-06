from typing import List

from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from gluon_meson_sdk.models.chat_model import ChatModel
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from loguru import logger

from nlu.base import EntityExtractor
from nlu.forms import FormStore, Form
from nlu.intent_with_entity import Entity
from prompt_manager.base import PromptManager
from tracker.context import ConversationContext

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

    def construct_messages(
        self,
        user_input,
        intent,
        form: Form,
        conversation_context: ConversationContext,
        preparation: ChatMessagePreparation,
    ) -> None:
        slots = form.get_available_slots_str()
        preparation.add_message(
            "system",
            self.slot_extraction_prompt.template,
            user_intent=intent.name,
            chat_history=conversation_context.get_history().format_string_with_file_name(),
            entity_types_and_values=slots,
        )
        for example in self.examples:
            preparation.add_message("user", example[0])
            preparation.add_message("assistant", example[1])
        preparation.add_message("user", user_input)

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

    async def extract_entity(self, conversation_context: ConversationContext) -> List[Entity]:
        user_input = conversation_context.current_user_input
        intent = conversation_context.current_intent
        form = self.form_store.get_form_from_intent(intent)
        if not form:
            logger.debug(f"this intent [{intent.name}] does not need to extract entity")
            return []

        chat_model = self.scenario_model_registry.get_model(self.scenario_model, log_id=conversation_context.session_id)

        # TODO: drop history if it is too long
        chat_message_preparation = ChatMessagePreparation()
        if not form.slots:
            return []
        self.construct_messages(user_input, intent, form, conversation_context, chat_message_preparation)
        chat_message_preparation.log(logger)
        entities = (
            await chat_model.achat(**chat_message_preparation.to_chat_params(), max_length=4096, jsonable=True)
        ).get_json_response()

        logger.debug(entities)
        if not entities:
            return []
        slot_name_to_slot = {slot.name: slot for slot in form.slots}
        print(f"slot_name_to_slot {slot_name_to_slot}")
        conversation_context.current_intent_slot_names = slot_name_to_slot.keys()

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
