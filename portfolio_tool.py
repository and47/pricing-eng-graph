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
        self.adj_list_parents = Nmspc()
        self.adj_list_parents.stocks = {}      # key names and values are parents (portfolios)
        self.adj_list_parents.stock_weights = {}  # identical structure for weights (dicts and values, which are lists, both are ordered in Python)
        self.adj_list_parents.portfolios = {}  # keys are (sub)portfolio names, values are lists of parent portfolios
        self.adj_list_parents.portfolio_weights = {}
        # self.adj_list_child.portfolios = {}  # keys are portfolio names, values are lists of children (stocks or portfolios)
        # self.adj_list_child.portfolio_weights = {}
        # self.incomplete_stocks = set()  # for lazy initialization of evaluation DAGs (keep track of partial graphs that can be made complete as new prices appear)

    def add_read_component(self, name, qty=None, parent=None):
        # interface, expects portfolio name or stock belonging to a known portfolio
        # e.g. as in portfolios.csv
        self.add_component(name, qty, parent)

    def add_component(self, name, qty=None, parent=None):
        # only fills adjacency list, actual initialization of nodes is done after to ensure each node is created only once
        if parent is not None:
            # assert parent is not None  # Should stock always belong to some portfolio?
            # assert qty is not None  # stock should always have number/multiplier
            if name in self.adj_list_parents.stocks:
                self.adj_list_parents.stocks[name].append(parent)  # only this needed not below 2 for defaultdict
                self.adj_list_parents.stock_weights[name].append(qty)  # can be a "subportfolio", not efficient to check here, instead will get reclassifed in self.fix_structure()
            else:
                self.adj_list_parents.stocks[name] = [parent]
                self.adj_list_parents.stock_weights[name] = [qty]
        else:
            if name not in self.adj_list_parents.portfolios:
                # self.portfolios_al[name]  # self.portfolios_al[name] = [] ensures key added to defaultdict
                # self.portfolio_weights[name]  # defaultdict
                self.adj_list_parents.portfolios[name] = []
                self.adj_list_parents.portfolio_weights[name] = []

    # @property?
    def merged_view(self):
        return ( ChainMap(self.adj_list_parents.portfolios, self.adj_list_parents.stocks),
                  ChainMap(self.adj_list_parents.portfolio_weights, self.adj_list_parents.stock_weights) )

    def fix_structure(self):
        # corrects adjacency lists that were built as data was "read in"
        to_move = [node for node in self.adj_list_parents.stocks if node in self.adj_list_parents.portfolios]
        for node in to_move:
            parents = self.adj_list_parents.stocks.pop(node)
            parent_weights = self.adj_list_parents.stock_weights.pop(node)
            self.adj_list_parents.portfolios[node].extend(parents)
            self.adj_list_parents.portfolio_weights[node].extend(parent_weights)
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
        # for faster lookup, replace tickers with ref indices in 1 adjacency list
        # self.graph.adj_list_child.portfolios = {self.all_refidx[k] : [self.all_refidx[v] for v in vs]
        #     for k, vs in self.graph.adj_list_child.portfolios.items()}


    def _init_nodes(self):
        for name, owners in self.adj_list_parents.stocks.items():
            # weights = self.stock_weights[name]
            self.stocks[name] = Stock(name, graph=proxy(self), price_refidx=self.all_refidx[name])
        for name, owners in self.adj_list_parents.portfolios.items():
            # weights = self.portfolio_weights[name]
            self.portfolios[name] = Portfolio(name,
                                              graph=proxy(self),
                                              price_refidx=self.all_refidx[name])

    def _link_nodes(self):
        for name, stock in self.stocks.items():
            # stock.owners.extend(self.stocks_al[name])  # add or refer to parents/direct owners
            for owner, w in zip(self.adj_list_parents.stocks[name], self.adj_list_parents.stock_weights[name]):
                self.portfolios[owner].weights.append(w)
                self.portfolios[owner].assets.append(stock.price_refidx)
        for name, portfolio in self.portfolios.items():
            for owner, w in zip(self.adj_list_parents.portfolios[name], self.adj_list_parents.portfolio_weights[name]):
                self.portfolios[owner].weights.append(w)
                self.portfolios[owner].assets.append(portfolio.price_refidx)


class Component:
    def __init__(self, name: str, price_refidx: int, graph: ProxyType, value: float = nan):
        self.name = name
        self.price_refidx = price_refidx
        self.graph = graph
        if isnan(value):
            self.is_active = False
        else:
            self.value = value
            self.is_active = True

    # keep prices centrally in a graph for a more efficient sum op
    @property
    def price(self):
        return self.graph.all_prices[self.price_refidx]

    @price.setter
    def price(self, value):
        if self.graph.all_prices[self.price_refidx] != value:
            self.graph.all_prices[self.price_refidx] = value
            self.print_value()

    def print_value(self, value=None):
        print(f"{self.name} value: {value if value else self.price}")

    # def activate(self, from_stock=None):
    #     """Upon first pricing, we can now compute all or only select downstream portfolios
    #     Establishes, which ones (conditional on presence of other component prices) and which order"""
    #     if not (self.is_active and self.is_complete):
    #         self.is_active = True
    #         self.is_complete = True
    #         owners = self.graph.merged_view()[0][self.name]
    #         owners_to_activate = owners.copy()
    #         for owner_name in owners:
    #             child_idxs = self.graph.adj_list_child.portfolios[owner_name]
    #             if any(isnan(self.graph.all_prices[child_idxs])):
    #                 if isinstance(self, Stock)
    #                 self.graph.incomplete_stocks.add(self.price_refidx)
    #                 self.is_complete = False
    #                 owners_to_activate.remove(owner_name)
    #         for owner_name in owners_to_activate:
    #             self.graph.portfolios[owner_name].activate()
    #         # do a toposort here from self on the active part of the graph
    #         #  if self is price and is not complete, on update of another price, if self is part of another's toposort, re-activate this self.
    #         if not owners:
    #             self.graph.adj_list_child.portfolios

    def update_parent_values(self, value_difference):
        """BFS (bottom-up) price updates for only affected portfolios and only if all input prices are present
        In multi-processing env can lock the tree being updated and only allow updates on disconnected subgraphs"""

        visited = [self.name]  # BFS visited nodes. name, weight (placeholder for 0th node)
        queue = [(self.name, 1)]  # BFS queue with weights (cumulative product)
        status = True  # early stop for BFS (affected nodes after a node that can't be priced)

        while queue:
            node, current_weight = queue.pop(0)
            if node != self.name:  # evaluate parent portfolios using cumulative (product of prior) weights:
                # self.graph.portfolios[node].update_value(value_difference * current_weight)
                status = self.graph.portfolios[node].update_value()  # incremental update doesn't work in some corner cases
            if status:
                for parent, weight in zip(self.graph.merged_view()[0][node],
                                          self.graph.merged_view()[1][node]):
                    if parent not in visited:
                        visited.append(parent)
                        queue.append((parent, current_weight * weight))


class Stock(Component):

    def update_value(self, new_value):
        old_value = self.price
        self.price = new_value
        # if isnan(old_value):
        #     self.activate()
        value_difference = new_value - old_value
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
        # print(f'...evaluating {self.name}')
        if not isnan(self.price) and not isnan(value_difference):
            self.price += value_difference
        elif any(isnan(px := self.asset_px)):
            return False
        else:  # first time value calculated (all component prices are present)
            self.price = dot(px, self.weights)
        return True

class Nmspc:
    pass
