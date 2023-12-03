import gm_logger
from action.action import Action
from tracker.context import ConversationContext
from nlu.mlm.entity import EntityExtractor
from nlu.mlm.intent import IntentClassifier
from nlu.mlm.mixed import MixedNLU
from policy.base import PolicyManager
from reasoner.base import Plan, Reasoner

logger = gm_logger.get_logger()

class LlmReasoner(Reasoner):

    def __init__(self, intent_classifier: IntentClassifier, entity_extractor: EntityExtractor,
                 policy_manager: PolicyManager, model_type: str):
        self.intent_classifier = intent_classifier
        self.entity_extractor = entity_extractor
        self.policy_manager = policy_manager
        self.nlu = MixedNLU(intent_classifier, entity_extractor)
        self.model_type = model_type

    def greet(self, conversation_tracker: ConversationContext) -> Action:
        return self.policy_manager.get_greet_action(conversation_tracker, self.model_type)

    def think(self, conversation: ConversationContext) -> Plan:
        conversation.set_status('reasoning')
        intent_with_entities = self.nlu.extract_intents_and_entities(conversation)
        action = self.policy_manager.get_action(intent_with_entities, conversation, self.model_type)

        return Plan(intent_with_entities, "", action, [])
