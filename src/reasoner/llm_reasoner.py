import gm_logger
from action_runner.action import Action
from conversation_tracker.context import ConversationContext
from nlu.llm.entity import EntityExtractor
from nlu.llm.intent import IntentClassifier
from nlu.llm.llm_nlu import LLMNlu
from policy_manager.base import PolicyManager
from reasoner.base import Plan, Reasoner

logger = gm_logger.get_logger()

class LlmReasoner(Reasoner):

    def __init__(self, intent_classifier: IntentClassifier, entity_extractor: EntityExtractor,
                 policy_manager: PolicyManager, model_type: str):
        self.intent_classifier = intent_classifier
        self.entity_extractor = entity_extractor
        self.policy_manager = policy_manager
        self.nlu = LLMNlu(intent_classifier, entity_extractor)
        self.model_type = model_type

    def greet(self, conversation_tracker: ConversationContext) -> Action:
        return self.policy_manager.get_greet_action(conversation_tracker, self.model_type)

    def think(self, conversation: ConversationContext) -> Plan:
        conversation.set_status('reasoning')
        intent_with_entities = self.nlu.extract_intents_and_entities(conversation)
        # todo: 需要补充一轮槽位，根据识别的意图，获取表单，然后从表单中获取槽位，有一些槽位是可以自动填充的，比如查天气，默认是今天，开灯的话，根据所对话的智能音箱所处的房间，自动填充房间。
        action = self.policy_manager.get_action(intent_with_entities, conversation, self.model_type)

        return Plan(intent_with_entities, "", action, [])
