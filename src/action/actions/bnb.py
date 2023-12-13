import configparser
from loguru import logger
from action.base import Action, ActionResponse, ActionName, ActionToSlotCategoryDict, SlotTypeToSlotValueTypeDict, \
    ActionToOperateTypeDict, ActionToValidSlotTypesDict, ActionResponseAnswerContent, ActionResponseAnswer, \
    JumpOutResponse
from output_adapter.base import OutputAdapter

config = configparser.ConfigParser()
config.read('config.ini')


class BankRelatedAction(Action):
    def __init__(self, action_name, possible_slots, intent, output_adapter: OutputAdapter):
        self.action_name = action_name
        self.possible_slots = possible_slots
        self.intent = intent
        self.output_adapter = output_adapter

    def run(self, context) -> ActionResponse:
        logger.info(f'exec action {self.action_name}')
        target_slots = [x for x in self.possible_slots if x.name in ActionToValidSlotTypesDict[self.action_name]]
        if len(target_slots) > 1:
            target_slots.sort(key=lambda x: x.priority, reverse=True)
        target_slot_value = self.output_adapter.normalize_slot_value(
            target_slots[0].value if len(target_slots) > 0 else config.get('defaultActionSlotValue',
                                                                           self.action_name))
        target_slot_name = self.output_adapter.normalize_slot_value(
            target_slots[0].name if len(target_slots) > 0 else ActionToValidSlotTypesDict[self.action_name][0])
        slot = dict()
        if self.action_name == ActionName.activate_function or self.action_name == ActionName.page_resize:
            slot = {
                "value": target_slot_value
            }
        elif self.action_name == ActionName.page_reduce or self.action_name == ActionName.page_enlarge:
            slot = {
                "category": ActionToSlotCategoryDict[self.action_name],
                "value": target_slot_value
            }

        elif self.action_name == ActionName.add_header or self.action_name == ActionName.remove_header:
            slot = {
                "category": ActionToSlotCategoryDict[self.action_name],
                "valueType": SlotTypeToSlotValueTypeDict[target_slot_name],
                "value": target_slot_value
            }

        answer = ActionResponseAnswer(messageType="FORMAT_INTELLIGENT_EXEC",
                                      content=ActionResponseAnswerContent(businessId="N35010Operate",
                                                                          operateType=ActionToOperateTypeDict[
                                                                              self.action_name],
                                                                          operateSlots=slot,
                                                                          businessInfo={}))

        return ActionResponse(code=200, message="success", answer=answer, jump_out_flag=False)


class JumpOut(Action):
    def __init__(self):
        pass

    def run(self, context) -> ActionResponse:
        logger.debug("非范围内意图")
        return JumpOutResponse(code=200, message="success", answer={}, jump_out_flag=True)
