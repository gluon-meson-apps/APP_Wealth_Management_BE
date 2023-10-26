from action_runner.action import Action, ActionResponse, GLUON_MESON_CONTROL_CENTER_ENDPOINT
from gluon_meson_sdk.models.chat_model import ChatModel


class RAGAction(Action):

    template = """
### 角色：假设你是保险产品专家，你的特点是逻辑性特别强，思维清晰，回答简明扼要，一般只回答和问题以及和具体产品相关的内容
### 任务：负责回答客户的问题，答案需要像聊天一样，但回答中不要向客户提及产品名称
 * 回答要依据产品的责任，避免使用“通常”、“一般情况下”、“一般”等用语
 * 请重点理解《重大疾病保险条款》中的核心逻辑
### 保险条款
```plantuml
@startuml

title 汇丰长佑康宁重大疾病保险的条款

start
if (仍在等待期并且未发生意外事故) then (是)
  if (是否确诊保险合同所定义的疾病?) then (是)
    :无息退还已交纳的保险费;
    :合同终止;
  endif
  stop
else (否)
    if (确诊保险合同所定义的疾病?) then (是)
      if (确诊轻症疾病?) then (是)
            if (首次确诊?) then (是)
                :给付首次轻症疾病保险金;
            elseif (第二次确诊?) then (是)
                :给付第二次轻症疾病保险金;
            elseif (第三次确诊?) then (是)
                :给付第三次轻症疾病保险金;
            else (第四次及以上确诊)
                :本项责任终止\n保险合同继续有效;
            endif
      elseif (首次确诊重大疾病?) then (是)
        :给付保险合同基本保险金额和已交保险费总额;
        :本项责任终止;
        :但保险合同的现金价值降为零;
      elseif (首次确诊特选重大疾病?) then (是)
        if (确诊过重大疾病?) then (是)
            :给付特选重大疾病补充保险金;
        else (否)
            :给付保险合同基本保险金额和已交保险费总额;
            :给付特选重大疾病补充保险金;
        endif
        :合同终止;
      elseif (是否确诊特定重度恶性肿瘤) then (是)
        :给付男女性特定恶性肿瘤保险金;
      elseif (是否确诊白血病) then (是)
        :给付白血病关爱保险金;
      elseif (是否身故或全残) then (是)
        :给付身故保险金或全残保险金;
      else (否)
        :保险合同继续有效;
      endif
    else (无需理赔)
        stop
    endif
endif
stop

@enduml
```
### 问题
Q:{question}
A:
"""

    def __init__(self, model_type: str, slots):
        self.model_type = model_type
        self.chat_model = ChatModel(control_center_endpoint=GLUON_MESON_CONTROL_CENTER_ENDPOINT)
        self.slots = slots

    def run(self, context) -> ActionResponse:
        question = self.get_slot('问题').value
        prompt = self.template.format(question=question)
        response = self.chat_model.chat_single(prompt, model_type=self.model_type, max_length=4096, temperature=0.01)
        return ActionResponse(text=response.response)

    def get_slot(self, slot_name):
        for slot in self.slots:
            if slot.name == slot_name:
                return slot
        return None
