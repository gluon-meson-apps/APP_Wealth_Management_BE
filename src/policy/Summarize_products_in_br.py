from typing import Tuple

from policy.base import Action, PromptManager
from action.repository.action_repository import ActionRepository, action_repository as default_action_repository
from forms import FormStore
from intent_with_entity import IntentWithEntity
from policy.base import Policy
from tracker.context import ConversationContext


class SummarizeProductsInBr(Policy):
    def __init__(self, prompt_manager: PromptManager, form_store: FormStore,
                 action_repository: ActionRepository = default_action_repository):
        Policy.__init__(self, prompt_manager)
        self.form_store = form_store
        self.action_repository = action_repository

    def handle(
            self, intent: IntentWithEntity, context: ConversationContext
    ) -> Tuple[bool, Action]:
        pass
    
    