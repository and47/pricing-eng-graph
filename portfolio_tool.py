from collections import ChainMap, defaultdict


class AssetGraph:
    # can be disconnected subgraphs of stocks and (optionally other portfolios) belonging to portfolios
    def __init__(self):
        self.stocks = defaultdict(list)      # leaves in a tree-like graph, key names and values are parents (portfolios)
        self.stock_weights = defaultdict(list)  # identical structure for weights (dicts and values, which are lists, are ordered in Python)
        self.portfolios = defaultdict(list)  # non-leaves in a tree-like graph, keys are portfolio names, values are lists of children (stocks or portfolios)
        self.portfolio_weights = defaultdict(list)

    def add_read_component(self, name, qty=None, parent=None):
        # interface, expects portfolio name or stock belonging to a known portfolio
        # e.g. as in portfolios.csv
        self.add_component(name, qty, parent)

    def add_component(self, name, qty=None, parent=None):
        if parent is not None:
            # assert parent is not None  # Should stock always belong to some portfolio?
            # assert qty is not None  # stock should always have number/multiplier
            self.stocks[name].append(parent)
            self.stock_weights[name].append(qty)
        else:
            if name not in self.portfolios:
                self.portfolios[name]  # self.portfolios[name] = [] ensures key added to defaultdict
                self.portfolio_weights[name]

    def merged_view(self):
        return ( ChainMap(self.stocks, self.portfolios),
                  ChainMap(self.stock_weights, self.portfolio_weights) )

    def fix_structure(self):
        to_move = [node for node in self.stocks if node in self.portfolios]
        for node in to_move:
            parents = self.stocks.pop(node)
            parent_weights = self.stock_weights.pop(node)
            self.portfolios[node].extend(parents)
            self.portfolio_weights[node].extend(parent_weights)
        # alternatively:
        # self.stocks = {node for node in self.stocks if node not in self.portfolios}
        # self.stock_weights = {node for node in self.stock_weights if node not in self.portfolios}
        # self.portfolios = {node for node in self.stocks if node in self.portfolios}
        # self.portfolio_weights = {node for node in self.stock_weights if node in self.portfolios}

class Component:
    def __init__(self, name):
        self.name = name
        self.parents = []  # Now a list to support multiple parents

    def add_parent(self, parent):
        if parent not in self.parents:
            self.parents.append(parent)

    def remove_parent(self, parent):
        if parent in self.parents:
            self.parents.remove(parent)

class Stock(Component):
    def __init__(self, name, size=0):
        super().__init__(name)
        self.value = value

    def update_value(self, new_value):
        old_value = self.value
        self.value = new_value
        value_difference = new_value - old_value
        print(f"{self.name} value updated from {old_value} to {new_value}")
        for parent in self.parents:
            parent.update_value(value_difference)

class Portfolio(Component):
    def __init__(self, name):
        super().__init__(name)
        self.children = []
        self.value = 0

    def add_child(self, component):
        if component not in self.children:
            component.add_parent(self)
            self.children.append(component)
            self.value += component.value

    def update_value(self, value_difference):
        self.value += value_difference
        print(f"{self.name} value: {self.value}")
        for parent in self.parents:
            parent.update_value(value_difference)

