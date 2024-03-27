from typing import List

from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from gluon_meson_sdk.models.chat_model import ChatModel
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from loguru import logger

from nlu.base import EntityExtractor
from nlu.forms import FormStore, Form
from nlu.intent_with_entity import Entity, SlotType, Slot, Intent
from prompt_manager.base import PromptManager
from tracker.context import ConversationContext
from utils.common import parse_str_to_bool

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
        intent: Intent,
        form: Form,
        conversation_context: ConversationContext,
        preparation: ChatMessagePreparation,
    ) -> None:
        self.construct_messages_cls(
            self.slot_extraction_prompt.template,
            intent.name,
            form,
            conversation_context.get_history().format_string_with_file_name(),
            conversation_context.get_file_name(),
            preparation,
        )

    @classmethod
    def construct_messages_cls(
        cls,
        slot_extraction_prompt,
        intent,
        form: Form,
        chat_history: str,
        file_names: str,
        preparation: ChatMessagePreparation,
    ):
        slots = form.get_available_slots_str()
        entity_list = form.get_slot_name_list()

        # todo: currently we do latest request summary twice(here and new topic check),
        #  should consider provide the latest request summary in one place.
        preparation.add_message(
            "system",
            slot_extraction_prompt,
            user_intent=intent,
            chat_history=chat_history,
            entity_list=entity_list,
            intent_description=form.intent_description,
            entity_types_and_values=slots,
            file_names=file_names,
        )

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
        intent: Intent = conversation_context.current_intent
        form = self.form_store.get_form_from_intent(intent)
        if not form:
            logger.debug(f"this intent [{intent.name}] does not need to extract entity")
            return []

        chat_model = await self.scenario_model_registry.get_model(
            self.scenario_model, log_id=conversation_context.session_id
        )

        # TODO: drop history if it is too long
        chat_message_preparation = ChatMessagePreparation()
        if not form.slots:
            conversation_context.current_intent_slots = []
            return []
        conversation_context.current_intent_slots = form.slots
        self.construct_messages(intent, form, conversation_context, chat_message_preparation)
        chat_message_preparation.log(logger)
        entities = (
            await chat_model.achat(**chat_message_preparation.to_chat_params(), max_length=1024, jsonable=True)
        ).get_json_response()
        logger.debug(f"extract entities: {entities}")

        bool_slots_entities = {
            slot.name: parse_str_to_bool(entities.get(slot.name) if entities else False)
            for slot in form.slots
            if slot.slot_type == SlotType.BOOLEAN
        }
        logger.debug(f"bool entities: {bool_slots_entities}")

        merged_entities = {**entities, **bool_slots_entities} if entities else bool_slots_entities

        logger.debug(f"final entities: {merged_entities}")

        slot_name_to_slot = {slot.name: slot for slot in form.slots}
        entity_list = [tup for tup in merged_entities.items() if tup[0] in slot_name_to_slot] if merged_entities else []
        if not entity_list:
            return []

        def get_slot(name, value):
            if slot_name_to_slot:
                if name in slot_name_to_slot:
                    origin_slot = slot_name_to_slot[name]
                    slot = origin_slot.copy(
                        update={
                            "value": value,
                        }
                    )
                    slot.confidence = 1
                    return slot
            return None

        def check_slot_value_valid(value) -> bool:
            return value is not None and (isinstance(value, int) or len(str(value)) > 0)

        slots: list[Slot] = [get_slot(name, value) for name, value in entity_list]
        available_slots = [slot for slot in slots if check_slot_value_valid(slot.value)]

        logger.debug(f"extracted slots: {available_slots}")
        return [Entity(type=s.name, value=s.value, possible_slot=s) for s in available_slots]
