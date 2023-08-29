from typing import List

from gluon_meson_sdk.models.chat_model import ChatModel

from conversation_tracker.context import ConversationContext
from nlu.forms import FormStore, Form
from nlu.full_llm.context import FullLlmConversationContext
from nlu.intent_with_entity import Entity, Slot

import re
import json

system_template = """
## 背景：
你是一个聊天机器人，你需要解析用户的消息，根据用户提供的实体选项，提取出相应的实体，如果没有找到对应的实体，不要自己编造

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

接下来我会给你几个示例：
"""

user_message_template = """==聊天历史==
{conversation_history}
==聊天历史结束==
用户消息：{user_message}
用户意图：{user_intent}
实体的可选值：{entity_names}
回复："""

examples = [
    (user_message_template.format(conversation_history="", user_intent="操作智能家居", user_message="帮忙打开客厅的灯",
                                  entity_names="位置[智能家居所处的房间]、操作[对智能家居进行的操作]、对象[哪一种智能家居]、操作值[操作的时候，需要考虑的参数]"),
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
    }
}
```"""),
    (user_message_template.format(conversation_history="""用户：帮忙打开客厅的灯
机器人：请问需要将客厅的灯调到多亮呢？""", user_intent="操作智能家居/补充信息",
                                  user_message="调到50%的亮度",
                                  entity_names="位置[智能家居所处的房间]、操作[对智能家居进行的操作]、对象[哪一种智能家居]、操作值[操作的时候，需要考虑的参数]"),
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


class EntityExtractor:
    def __init__(self, form_store: FormStore, chat_model: ChatModel):
        self.form_store = form_store
        self.model = chat_model

    def construct_messages(self, user_input, intent, form: Form, history="") -> List[str]:
        final_user_message = user_message_template.format(conversation_history=history, user_intent=intent,
                                                          user_message=user_input,
                                                          entity_names=form.get_available_slots_str())
        history = [('system', system_template)]
        for example in examples:
            history.append(('user', example[0]))
            history.append(('assistant', example[1]))
        return final_user_message, history

    def extract_json_code(self, response) -> str:
        return re.match('```((.|\n)*)```', response).group(1)

    def extract_entity(self, conversation_context: FullLlmConversationContext) -> List[Entity]:
        user_input = conversation_context.get_current_user_input()
        intent = conversation_context.get_current_intent()
        form = self.form_store.get_form_from_intent(intent)
        slot_name_to_slot = {slot.name: slot for slot in form.slots}
        prompt, history = self.construct_messages(user_input, intent, form)
        response = self.model.chat_single(prompt, history=history, model_type="qwen", max_length=2048).response
        entities = json.loads(self.extract_json_code(response))

        def get_slot(name, value):
            if name in slot_name_to_slot:
                return slot_name_to_slot[name].copy(update={'value': value['value']})
            else:
                return None

        return [Entity(type=name, value=value['value'], possible_slot=get_slot(name, value)) for name, value in
                entities.items()]


if __name__ == '__main__':
    extractor = EntityExtractor(FormStore(), ChatModel())
    print(
        extractor.extract_entity(FullLlmConversationContext(ConversationContext("帮忙把字体调大一点点", "页面字体缩放"))))
