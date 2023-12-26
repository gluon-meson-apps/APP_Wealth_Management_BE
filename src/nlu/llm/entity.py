import re
from typing import List

import yaml

from nlu.base import EntityExtractor
from tracker.context import ConversationContext
from gluon_meson_sdk.models.chat_model import ChatModel
from loguru import logger
from nlu.forms import FormStore, Form
from nlu.intent_with_entity import Entity
from prompt_manager.base import PromptManager

system_template = """
## Role & Task
你是一个聊天机器人，你需要根据"User Intent"和"Chat History"，结合提供的"Entities Types & Description"，提取出相应的实体。
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
        self.user_message_template = prompt_manager.load("slot_extraction_user_message")
        self.examples = self.prepare_examples()

    def construct_messages(
        self, user_input, intent, form: Form, conversation_context: ConversationContext
    ) -> List[str]:
        chat_history = conversation_context.get_history().format_string()
        final_user_message = self.user_message_template.format(
            {
                "chat_history": chat_history,
                "user_intent": intent.name,
                "user_message": user_input,
                "entity_types_and_values": form.get_available_slots_str(),
            }
        )
        history = [("system", system_template)]
        for example in self.examples:
            history.append(("user", example[0]))
            history.append(("assistant", example[1]))
        return final_user_message, history

    def prepare_examples(self):
        examples = [
            (
                self.user_message_template.format(
                    {
                        "chat_history": "user: 帮忙打开客厅的灯",
                        "user_intent": "控制智能家居",
                        "entity_types_and_values": "位置[智能家居所处的房间]、操作[对智能家居进行的操作]、对象[哪一种智能家居]、操作值[操作的时候，需要考虑的参数]",
                    }
                ),
                """```yaml
位置: 客厅
操作: 打开
对象: 灯
操作值: 开启
```""",
            ),
            (
                self.user_message_template.format(
                    {
                        "chat_history": """user: 帮忙调亮客厅的灯
        assistant: 请问需要将客厅的灯调到多亮呢？
        user: 调到50%的亮度""",
                        "user_intent": "控制智能家居/补充信息",
                        "entity_types_and_values": "位置[智能家居所处的房间]、操作[对智能家居进行的操作]、对象[哪一种智能家居]、操作值[操作的时候，需要考虑的参数]",
                    }
                ),
                """```yaml
 位置: 客厅
 操作: 打开
 对象: 灯
 操作值: 0.5
 ```""",
            ),
        ]
        return examples

    def extract_yaml_code(self, response) -> str:
        logger.debug(response)
        return re.match("```yaml((.|\n)*)```", response).group(1)

    def extract_entity(self, conversation_context: ConversationContext) -> List[Entity]:
        user_input = conversation_context.current_user_input
        intent = conversation_context.current_intent
        form = self.form_store.get_form_from_intent(intent)
        if not form:
            logger.debug(f"该意图[{intent.name}]不需要提取实体")
            return []
        prompt, history = self.construct_messages(
            user_input, intent, form, conversation_context
        )
        logger.debug(prompt)
        response = self.model.chat_single(
            prompt, history=history, max_length=2048, model_type="azure-gpt-3.5-2"
        )
        entities = yaml.safe_load(self.extract_yaml_code(response.response))
        slot_name_to_slot = {slot.name: slot for slot in form.slots}
        if entities:
            entity_list = list(
                filter(
                    lambda tup: tup[0] in slot_name_to_slot
                    and tup[1] is not None
                    and (isinstance(tup[1], int) or len(tup[1]) > 0),
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

        return [
            Entity(type=name, value=value, possible_slot=get_slot(name, value))
            for name, value in entity_list
        ]
