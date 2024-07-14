# PoC for a graph-based Pricing (linear/delta Risk) Engine

Value portfolios from component prices (dependency graph).

Features: "composite" OOP design pattern, generators, BFS level-order traversal implementation with weights, 2 valuation approaches (2nd requires only single traversal at initialization). Weakref is used to just demo avoiding circular reference, which is however not a problem here due to how instances are created and linked.

To-do:
- use dataclasses for typed class attributes
- add multi-processing; lock subgraphs (the tree that is being updated) and only allow updates on disconnected subgraphs
- currently allows and does not catch cycles in a graph, which may be expected. alternatively, could've used Kahn's algorithm for toposort
- could've used observer design pattern, making further use of weakref, with added benefit of more dynamic (during use) of portfolio definitions, e.g. portfolio removal, etc.
