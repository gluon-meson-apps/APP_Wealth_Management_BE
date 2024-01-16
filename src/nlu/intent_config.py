import os

import yaml


class IntentConfig:
    def __init__(self, name, description, business, action, slots, examples=None):
        self.name = name
        self.description = description
        self.action = action
        self.slots = slots
        self.business = business
        self.examples = examples or []

    def minial_info(self):
        return {
            "name": self.name,
            "description": self.description,
        }


class IntentListConfig:
    def __init__(self, intents: list[IntentConfig]):
        self.intents = intents
        self._initialize_fixed_intents()

    def _initialize_fixed_intents(self):
        fixed_intents = [
            ("positive", "confirm", False, "positive", []),
            ("negative", "denied", False, "negative", []),
        ]

        for intent_data in fixed_intents:
            name, description, business, action, slots = intent_data
            intent = IntentConfig(name, description, business, action, slots)
            self.intents.append(intent)

    def get_intent_list(self) -> list[IntentConfig]:
        return self.intents

    def get_intent_name(self):
        # read resources/intent.yaml file and get intent list
        return [intent.name for intent in self.intents if intent.name != "unknown"]

    def get_intent(self, intent_name):
        return next((intent for intent in self.intents if intent.name == intent_name), None)

    def get_intent_and_attrs(self):
        return [
            {
                "intent": intent.name,
                "examples": intent.examples,
                "description": intent.description,
            }
            for intent in self.intents
        ]

    @classmethod
    def from_scenes(cls, folder_path):
        intents = []
        files = [f for f in os.listdir(folder_path) if f.endswith(".yaml")]

        for file_name in files:
            file_path = os.path.join(folder_path, file_name)

            with open(file_path, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file)

            intent = IntentConfig(
                name=data.get("name"),
                description=data.get("description"),
                business=data.get("business"),
                action=data.get("action"),
                slots=data.get("slots"),
            )
            intents.append(intent)

        return cls(intents)
