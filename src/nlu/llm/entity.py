import json
import re
from typing import List

from conversation_tracker.context import ConversationContext
from gluon_meson_sdk.models.chat_model import ChatModel
from gm_logger import get_logger
from nlu.forms import FormStore, Form
from nlu.intent_with_entity import Entity
from prompt_manager.base import PromptManager

logger = get_logger()

system_template = """
## 角色与任务
你是一个聊天机器人，你需要根据识别出的用户意图和聊天历史，结合提供的实体选项，提取出相应的实体。
如果没有找到对应的实体，输出空字符串，数值型的实体，需要输出的是用户明确表示的具体数值。

## 返回格式
返回格式必须符合json格式，下面是一个返回的例子：
{
    "实体1": {
        "实体值": "$实体值"
    },
    ...
    "实体n": {
        "实体值": "$实体值"
    }
}

重点关注必选的实体
"""


class EntityExtractor:
    def __init__(self, form_store: FormStore, chat_model: ChatModel, model_type: str, prompt_manager: PromptManager):
        self.form_store = form_store
        self.model = chat_model
        self.model_type = model_type
        self.prompt_manager = prompt_manager
        self.user_message_template = prompt_manager.load('slot_extraction_user_message')
        self.examples = self.prepare_examples()

    def construct_messages(self, user_input, intent, form: Form, conversation_context: ConversationContext) -> List[str]:
        chat_history = conversation_context.get_history().format_to_string()
        final_user_message = self.user_message_template.format({"chat_history": chat_history,
                                                                "user_intent": intent.name,
                                                                "user_message": user_input,
                                                                "entity_types_and_values": form.get_available_slots_str()})
        history = [('system', system_template)]
        for example in self.examples:
            history.append(('user', example[0]))
            history.append(('assistant', example[1]))
        return final_user_message, history

    def prepare_examples(self):
        examples = [
            (self.user_message_template.format({"chat_history": "user: 帮忙打开客厅的灯", "user_intent": "控制智能家居",
                                                "entity_types_and_values": "位置[智能家居所处的房间]、操作[对智能家居进行的操作]、对象[哪一种智能家居]、操作值[操作的时候，需要考虑的参数]"}),
             """```
        {
            "位置": {
                "value": "客厅"
            },
            "操作": {
                "value": "打开"
            },
            "对象": {
                "value": "灯"
            },
            "操作值": {
                "value": "开启"
            }
        }
        ```"""),
            (self.user_message_template.format({"chat_history": """user: 帮忙调亮客厅的灯
        assistant: 请问需要将客厅的灯调到多亮呢？
        user: 调到50%的亮度""", "user_intent": "控制智能家居/补充信息",
                                                "entity_types_and_values": "位置[智能家居所处的房间]、操作[对智能家居进行的操作]、对象[哪一种智能家居]、操作值[操作的时候，需要考虑的参数]"}),
             """```
        {
            "位置": {
                "value": "客厅"
            },
            "操作": {
                "value": "打开"
            },
            "对象": {
                "value": "灯"
            },
            "操作值": {
                "value": "0.5"
            }
        }
        ```"""),
        ]
        return examples

    def extract_json_code(self, response) -> str:
        logger.debug(response)
        return re.match('```((.|\n)*)```', response).group(1)

    def extract_entity(self, conversation_context: ConversationContext) -> List[Entity]:
        user_input = conversation_context.current_user_input
        intent = conversation_context.current_intent
        form = self.form_store.get_form_from_intent(intent)
        if not form:
            logger.debug(f"该意图[{intent.name}]不需要提取实体")
            return []
        prompt, history = self.construct_messages(user_input, intent, form, conversation_context)
        logger.debug(prompt)
        response = self.model.chat_single(prompt, history=history, model_type=self.model_type,
                                          max_length=2048).response
        entities = json.loads(self.extract_json_code(response))
        entity_list = list(filter(lambda tup: len(tup[1]) > 0, list(entities.items())))
        slot_name_to_slot = {slot.name: slot for slot in form.slots}

        def get_slot(name, value):
            if slot_name_to_slot:
                if name in slot_name_to_slot:
                    return slot_name_to_slot[name].copy(update={'value': value['value']})
            return None

        return [Entity(type=name, value=value['value'], possible_slot=get_slot(name, value)) for name, value in
                entity_list]


