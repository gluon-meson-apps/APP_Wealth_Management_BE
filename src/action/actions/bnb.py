from loguru import logger
from action.base import Action, ActionResponse, ActionToValidSlotTypesDict, JumpOutResponse
from output_adapter.base import OutputAdapter
import configparser

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
        target_slots = self.get_target_slots()
        target_slot_value, target_slot_name = self.get_target_slot_name_and_value(target_slots)
        slot = self.output_adapter.prepare_slot(self.action_name, target_slot_value, target_slot_name)
        answer = self.output_adapter.prepare_answer(slot, self.intent.description,
                                                    target_slot_value, target_slot_name, self.action_name)
        return ActionResponse(code=200, message="success", answer=answer, jump_out_flag=False)

    def get_target_slots(self):
        target_slots = [x for x in self.possible_slots if x.name in ActionToValidSlotTypesDict[self.action_name]]
        if len(target_slots) > 1:
            target_slots.sort(key=lambda x: x.priority, reverse=True)
        return target_slots

    def get_target_slot_name_and_value(self, target_slots: []):
        target_slot_name = self.output_adapter.get_slot_name(self.action_name, target_slots)
        slot_value = self.output_adapter.get_slot_value(target_slot_name, target_slots)
        target_slot_value = self.output_adapter.normalize_slot_value(
            slot_value,
            target_slot_name,
            self.action_name
        )

        return target_slot_value, target_slot_name


class JumpOut(Action):
    def __init__(self):
        pass

    def run(self, context) -> ActionResponse:
        logger.debug("非范围内意图")
        return JumpOutResponse(code=200, message="success", answer={}, jump_out_flag=True)
