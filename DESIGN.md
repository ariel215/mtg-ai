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

## Actions, Choices and the Stack

Actions are things that modify the game state. since we're interested
in exploring the game space, we need to think about not only
actions in the singular but sets of possible actions. These
sets can arise either from analyzing the game state, when
a player has priority, or because a card calls for a choice to be
made (Giant Growth, Collected Company, fetch lands).

Consider: you control two creatures and go to cast Giant Growth.
You are asked to chose a target before putting the card on the stack.
What does this look like?


> - Ask PlayCard(Giant Growth): Can I do this?
    - Can I pay all costs?
      * PlayCard: Is there more mana in the pool than in the card's cost? 
    - Can I make all choices?
      * PlayCard: choose targets for all effects on the card, if any
      - Ask the card's effect: what can you target?
      * {Suntail Hawk, Grizzly Bears}
  - if so: do it
    - pay cost
    - select an element of the choice set
    - do the effect to the gamestate with the choice made
      * gamestate.cast(giant growth, targets=[grizzly bears])
        * giant_growth.set(targets=[grizzly_bears])

Conceptually, selecting targets is just another kind of cost, in that it's
a thing that needs to be possible before you can take the action. Similarly,
for some kinds of costs (e.g. discarding a card, delving) there might be
more than one way to pay it.

So really the question we need to ask is: is there at least one way to do
everything we need to do?
if so, we do it with the selected choice set

so a Choice here is a collection of some kind, probably labelled?
And a ChoiceSet is what it sounds like, a set of choices.    

## Triggers

Triggers are effects that go onto the stack when "something happens".
What constitutes "something"?  There are no real boundaries, but probably
80% of triggers are triggered by a card changing zones: etbs, dying,
leaving, drawing, discarding, milling, are all special cases of a card changing
zones. The next 5-10% are delayed triggers that occur at the beginning of a
step or phase, attacking, blocking, and becoming tapped or untapped.

There's also two types of triggers: triggers that care about what the card
they're on does, and triggers that care about what other cards do. Wall of Omens
vs Arcades. The latter are only active while the card is in a specific zone,
typically in play but sometimes in the graveyard.

This is similar to static abilities: in both cases there's an effect that
is live for as long as some permanent remains in play, either a static
modifier or something watching for triggers. We need to be able to make sure
its lifespan is tied to its card.

The components of a triggered ability are: 
- The action that triggers it
  - This might be tied to a particular player or card or set of cards
- The object perfoming the action
- The object creating the trigger
- The effect of the trigger

Breaking down Wall of Omens'ability -- "When CARDNAME enters the battlefield, draw a card" in this way:
- the triggering action is: a card enters the battlefield
  - the action is triggered if: the card is CARDNAME
- the object performing the action: CARDNAME
- the object creating the trigger: CARDNAME
- the effect: CARDNAME's owner draws a card

