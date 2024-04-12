from collections import ChainMap, defaultdict
from weakref import proxy, ProxyType
from numpy import nan, isnan, ndarray, array, full, dot#, sum
# import numpy as np

# @dataclass
class AssetGraph:
    # all_prices: ndarray
    # all_refidx: dict

    # can be disconnected subgraphs of stocks and (optionally other portfolios) belonging to portfolios
    def __init__(self):
        self.stocks = {}  # leaves in a tree-like graph, actual nodes
        self.portfolios = {}  # non-leaves in a tree-like graph, actual nodes including "roots" (top-level portfolios if needed)
        # intermediate structures, from which graph is constructed:
        # self.stocks_al = defaultdict(list)      # key names and values are parents (portfolios)
        # self.stock_weights = defaultdict(list)  # identical structure for weights (dicts and values, which are lists, are ordered in Python)
        # self.portfolios_al = defaultdict(list)  # keys are portfolio names, values are lists of children (stocks or portfolios)
        # self.portfolio_weights = defaultdict(list)
        self.stocks_al = {}      # key names and values are parents (portfolios)
        self.stock_weights = {}  # identical structure for weights (dicts and values, which are lists, are ordered in Python)
        self.portfolios_al = {}  # keys are portfolio names, values are lists of children (stocks or portfolios)
        self.portfolio_weights = {}

    def add_read_component(self, name, qty=None, parent=None):
        # interface, expects portfolio name or stock belonging to a known portfolio
        # e.g. as in portfolios.csv
        self.add_component(name, qty, parent)

    def add_component(self, name, qty=None, parent=None):
        # only fills adjacency list, actual initialization of nodes is done after to ensure each node is created only once
        if parent is not None:
            # assert parent is not None  # Should stock always belong to some portfolio?
            # assert qty is not None  # stock should always have number/multiplier
            if name in self.stocks_al:
                self.stocks_al[name].append(parent)  # only this needed not below 2 for defaultdict
                self.stock_weights[name].append(qty)
            else:
                self.stocks_al[name] = [parent]
                self.stock_weights[name] = [qty]
        else:
            if name not in self.portfolios_al:
                # self.portfolios_al[name]  # self.portfolios_al[name] = [] ensures key added to defaultdict
                # self.portfolio_weights[name]  # defaultdict
                self.portfolios_al[name] = []
                self.portfolio_weights[name] = []

    # @property?
    def merged_view(self):
        return ( ChainMap(self.portfolios_al, self.stocks_al),
                  ChainMap(self.portfolio_weights, self.stock_weights) )

    def fix_structure(self):
        # corrects adjacency lists that were built as data was "read in"
        to_move = [node for node in self.stocks_al if node in self.portfolios_al]
        for node in to_move:
            parents = self.stocks_al.pop(node)
            parent_weights = self.stock_weights.pop(node)
            self.portfolios_al[node].extend(parents)
            self.portfolio_weights[node].extend(parent_weights)
        # alternatively:
        # self.stocks_al = {node for node in self.stocks_al if node not in self.portfolios_al}
        # self.stock_weights = {node for node in self.stock_weights if node not in self.portfolios_al}
        # self.portfolios_al = {node for node in self.stocks_al if node in self.portfolios_al}
        # self.portfolio_weights = {node for node in self.stock_weights if node in self.portfolios_al}
        self.init_components()

    def init_components(self):
        self._init_prices()  # create a central prices array and map locating their tickers
        # 2 steps: init all nodes, then "fill info about edges" (parents/children all initialized)
        self._init_nodes()
        self._link_nodes()  # this can be done with a reverse map, instead inverse relations are kept in nodes

    def _init_prices(self):
        self.all_prices = full(len(self.merged_view()[0]), nan)  # numpy array for efficient sum, ordered per dict
        self.all_refidx = {ticker: i for i, ticker in enumerate(self.merged_view()[0].keys())}  # tickers mapped to indices into array

    def _init_nodes(self):
        for name, owners in self.portfolios_al.items():
            # weights = self.portfolio_weights[name]
            self.portfolios[name] = Portfolio(name,
                                              graph=proxy(self),
                                              price_refidx=self.all_refidx[name])
        for name, owners in self.stocks_al.items():
            # weights = self.stock_weights[name]
            self.stocks[name] = Stock(name, graph=proxy(self), price_refidx=self.all_refidx[name])

    def _link_nodes(self):
        for name, stock in self.stocks.items():
            # stock.owners.extend(self.stocks_al[name])  # add or refer to parents/direct owners
            for owner, w in zip(self.stocks_al[name], self.stock_weights[name]):
                self.portfolios[owner].weights.append(w)
                self.portfolios[owner].assets.append(stock.price_refidx)
        for name, portfolio in self.portfolios.items():
            for owner, w in zip(self.portfolios_al[name], self.portfolio_weights[name]):
                self.portfolios[owner].weights.append(w)
                self.portfolios[owner].assets.append(portfolio.price_refidx)


class Component:
    def __init__(self, name: str, price_refidx: int, graph: ProxyType, value: float = nan):
        self.name = name
        self.price_refidx = price_refidx
        self.graph = graph

    def add_parent(self, parent):
        if parent not in self.owners:
            self.owners.append(parent)

    def remove_parent(self, parent):
        if parent in self.owners:
            self.owners.remove(parent)

    # keep prices centrally in a graph for a more efficient sum op
    @property
    def price(self):
        return self.graph.all_prices[self.price_refidx]

    @price.setter
    def price(self, value):
        self.graph.all_prices[self.price_refidx] = value

    def update_parent_values(self, value_difference):
        """Bottom-up price updates for only affected portfolio and only if all input prices are present
        In multi-processing env can lock the tree being updated and only allow updates on disconnected subgraphs"""
        all_owners_weights = self.graph.merged_view()
        for owner, weight in zip(all_owners_weights[0][self.name],
                                 all_owners_weights[1][self.name]):
            self.graph.portfolios[owner].update_value(value_difference * weight)

    def print_value(self, value = None):
        print(f"{self.name} value: {value if value else self.price}")


class Stock(Component):

    def update_value(self, new_value):
        old_value = self.price
        self.price = new_value
        value_difference = new_value - old_value
        self.print_value()
        self.update_parent_values(value_difference)


class Portfolio(Component):
    def __init__(self, name: str, price_refidx: int, graph: ProxyType, value: float = nan):
        super().__init__(name, price_refidx, graph, value)
        # lists of int:
        self.assets = []
        self.weights = []

    @property
    def asset_px(self) -> ndarray:
        return self.graph.all_prices[self.assets]

    def update_value(self, value_difference=nan):
        """Supports fully recomputing portfolio or incremental update from single new asset price"""
        if not isnan(self.price) and not isnan(value_difference):
            self.price += value_difference
        elif any(isnan(px := self.asset_px)):
            return None
        else:  # first time value calculated (all component prices are present)
            self.price = dot(px, self.weights)
        self.print_value()
        self.update_parent_values(value_difference)

