# A system for MtG Game Trees

A game of MtG can be very complicated, but comes down to
the permutation of 60 or 120 cards amidst a couple dozen possible
states.

Since cards can have 1-2 abilities and those abilities can
go on the stack, spawning a new object, we get ~1000 objects
over the course of a game.

Describing the evolution of a game requires modelling changes as
functions from gamestates to game states. For example:

```python
  game = game.play(card)
  game = game.activate(ability)
  game = game.resolve_stack()
  game = game.stack_triggers()
```

there is an obstacle here: game objects reference other game objects;
when we evolve the game state, the objects in the new state should all
reference each other and not the objects in the previous state.

```python
  class GameState:
  ...
    def play(self, card):
      new_game = self.copy()
      new_card = new_game.get(card)
      new_card.move_to(Zone.Field)
      return new_game
```

What should `Game.copy` do? It should copy all the game objects inside,
and update which game state owns them.

A design:
```python
  class GameState:
    objects: Dict[Id, GameObject]
    ...
    
    def copy(self)->GameState:
      new_game = GameState()
      # copy over non-object properties
      ...
      # copy game objects
      new_game.objects = {
        object.uid: object.copy(game_state=new_game)
        for object in self.objects
        }

    def get(self, obj:GameObject):
      return self.objects[obj.uid]

  @dataclass
  class GameObject:
      uid: Id
      game_state: GameState
      ...

      def find(self, new_state: GameState)->GameObject:
        """
        Returns the corresponding game object as it exists in the
        new game state
        """
        return new_state.objects[self.uid]
```

Given this, let's say our GameObject needs to hold a reference to some other
GameObject. We can use the descriptor protocol to keep these references
syncronized as the game state evolves:

```python
  class GameObjectRef:

  def __set__(self, owner: GameObject, referent:GameObject):
    owner._referent = referent.uid

  def __get__(self, owner, name):
    return owner.game_state.objects[owner._referent]
```

To work through how this works, let's walk through some situations.

First, let's say a.x = b, and a.game_state = b.game_state = G0.
What actually happens is a._referent = b.uid. Then when we
want to print(a.x), this turns into print(a.game_state[a._referent])
= print(G0[b.uid) = print(b). So far so good.

NOw let's update the state: G1=G0.change(b).
G1.objects = {
  a.uid: a_new,
  b.uid: b_new
}

So importantly, a.x still resolves to b. This is good; history needs to be
immutable.

But G1.get(a).x == G1.get(a.x) == a_new.x == b_new. We can easily track objects
between game states as they change.  

(Minor ergonomics question: does it make more sense to have
GameState.get or GameObject.find_in?)




