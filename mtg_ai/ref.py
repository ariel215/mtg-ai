"""
The problem is this: we have an implicit graph of objects, and want to make a
copy of the graph on demand. Also, when we do so, we want to create differently
colored edges between corresponding objects in each graph. 

The solution is this:
we store all our objects in an array, and use descriptors to
replace references between objects with indices into this array.

When we need to make a copy, we make a copy of the array. Since objects'
positions don't change, refs are still valid.

This system requires several parts:
1) Every object participating in this system needs to
   be initialized inside a global array

2) References to these objects need to be converted to indices
   semi-transparently

3) changes to objects inside history create a new world state

"""
from functools import wraps
from typing import List


class World:
    def __init__(self):
        self.entities = []
        self.parent: 'World' | None = None
        self.children: List[World] = []

    def add_entity(self, entity) -> int:
        idx = len(self.entities)
        self.entities.append(entity)
        return idx

    def update(self, new_entity) -> 'World':
        idx =getattr(new_entity,_REF_NAME)
        new_world = World()
        new_world.entities = [ent for ent in self.entities]
        new_world.entities[idx] = new_entity

        new_world.parent = self
        self.children.append(new_world)
        return new_world


class History:

    def __init__(self):
        self.root = World()

_REF_NAME='__ref_idx'


def reference(history: History):
    """
    Class decorator for classes participating in a history
    Modifies the init method to insert objects into the
    root world of the history
    """
    def replace_init(cls):
        orig_init = cls.__init__

        @wraps(orig_init)
        def new_init(self, *args, **kwargs):
            orig_init(self, *args, **kwargs)
            idx = history.root.add_entity(self)
            setattr(self,_REF_NAME,idx)
        
        cls.__init__ = new_init
        return cls

class ReferenceError(Exception):
    pass

class Ref:
    """
    Descriptor that replaces references
    with lookups via refs.ref_array, allowing
    transparent immutability. 
    """
    def __init__(self, world:World):
        self.world = world 

    def __set_name__(self, owner, name):
        self.private_name = f"_{name}"
        self.public_name =name

    def __set__(self, owner, value):
        index =getattr(value, _REF_NAME,None)
        if index is None:
            raise ReferenceError(
                f"Cannot assign {value} to field {self.public_name} of {owner}:"
                f"{value} must be wrapped in @reference") 
        setattr(owner,self.private_name,index)

    def __get__(self,owner, _objtype):
        return ref_lst[self.gen][getattr(owner,self.private_name)]

    def frozen(self):
        copy = Ref()
        copy.gen = len(ref_lst)
        copy.private_name = self.private_name
        return copy
    
