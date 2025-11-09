
class ChangeTracker:

    all_changes = []

    def __init__(self):
        self.changes = defaultdict(list)
        self.change_from = defaultdict(list)
        self.change_to = defaultdict(list)

    def __set_name__(self,owner, name):
        self.private = f"_{name}"

    def __get__(self, obj, _objtype):
        return getattr(obj,self.private)

    def __set__(self, obj, value):
        old_value = getattr(obj, self.private,None)

        old_kind = type(old_value)
        new_kind = type(new_value)
        if value != old_value:
            for callback in self.changes[(old_kind,new_kind)]:
                callback(obj, old_value, value)
            for callback in (
                    self.change_from[old_kind] + 
                    self.change_from[Any] + 
                    self.change_to[new_kind]):
                callback(obj)
            for callback in ChangeTracker.all_changes:
                callback(obj, old_value, value)
            setattr(obj,self.private,value)

    
    def on_draw(self, callback):
        self.changes[(Deck, Hand)].append(callback)
    
    
    def on_discard(self, callback):
        self.changes[(Hand,Grave)].append(callback)

    
    def on_cast(self, callback):
        self.changes[(Hand, Stack)].append(callback)

    
    def on_enters(self, callback): 
        self.change_to[Field].append(callback)
    
    
    def on_leaves(self, callback):
        self.change_from[Field].append(callback)

    
    def on_change(self, callback):
        self.change_from[Any].append(callback)
