class ActionContext:

    """Holds context information for executing actions."""
    
    def __init__(self, conversation):
        """Initialize empty context."""
        self.user_input = None
        self.slots = {}
        self.conversation = conversation
        
    def set_user_input(self, user_input):
        """Set the user input for this context."""
        self.user_input = user_input

    def get_user_input(self):
        """Get the user input."""
        return self.user_input

    def set_slot(self, name, value=None):
        """Set a slot value by name."""
        self.slots[name] = value

    def get_slot(self, name):
        """Get a slot value by name."""
        return self.slots.get(name)

    def get_slots(self):
        """Get all slots."""
        return self.slots

    def set_status(self, status):
        """Set the status of the conversation."""
        self.conversation.set_status(status)