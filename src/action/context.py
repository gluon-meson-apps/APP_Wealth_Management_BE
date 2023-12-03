class ActionContext:

    """Holds context information for executing actions."""
    
    def __init__(self, conversation):
        """Initialize empty context."""
        self.conversation = conversation

    def set_status(self, status):
        """Set the status of the conversation."""
        self.conversation.set_status(status)