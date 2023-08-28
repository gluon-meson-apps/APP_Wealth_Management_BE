from typing import List

from policy_manager.policy import Policy


class PolicyManager:
    def get_action(self, intent):
        pass


class BasePolicyManager(PolicyManager):
    def __init__(self, policies: List[Policy]):
        self.policies = policies

    def get_action(self, intent: str) -> str:
        pass