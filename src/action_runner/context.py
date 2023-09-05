
class ActionContext:

    def __init__(self):
        self.user_input = None 
        self.slots = {}
        
    def set_user_input(self, user_input):
        self.user_input = user_input
        
    def get_user_input(self):
        return self.user_input
    
    def set_slot(self, name, value):
        self.slots[name] = va·lue
        
    def get_slot(self, name):
        return self.slots.get(name)
    
    def get_slots(self):
        return self.slots