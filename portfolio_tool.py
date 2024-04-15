from collections import ChainMap
from weakref import proxy, ProxyType
from numpy import nan, isnan, ndarray, full, dot
from typing import Iterable


class Component:
    """Composite design pattern to universally represent graph Nodes (whether stocks or portfolios)"""
    def __init__(self, name: str, price_refidx: int, graph: ProxyType):
        self.name = name
        self.price_refidx = price_refidx
        self.graph = graph

    @property
    def price(self) -> float:
        """keep prices centrally in a graph for more efficient sum ops (ufunc)"""
        return self.graph.all_prices[self.price_refidx]

    @price.setter
    def price(self, value: float):
        if self.price != value:
            self.graph.all_prices[self.price_refidx] = value
            self.print_value()

    def print_value(self, value: float | None = None):
        print(f"{self.name},{value if value else self.price}")

    def update_parent_values(self, value_difference):
        """BFS (bottom-up) price updates for only affected portfolios and only if all input prices are present
        In multi-processing env can lock the tree being updated and only allow updates on disconnected subgraphs"""

        visited = [self.name]  # BFS visited nodes. name, weight (placeholder for 0th node)
        queue = [(self.name, 1)]  # BFS queue with weights (cumulative product, the weight is currently unused, see below)
        status = True  # early stop for BFS (affected nodes after a node that can't be priced)

        while queue:
            node, current_weight = queue.pop(0)
            if node != self.name:  # evaluate parent portfolios using cumulative (product of prior) weights:
                # self.graph.portfolios[node].update_value(value_difference * current_weight)
                status = self.graph.portfolios[node].update_value()  # incremental update abandoned after own test cases
            if status:
                for parent, weight in zip(self.graph.merged_view[0][node],
                                          self.graph.merged_view[1][node]):
                    if parent not in visited:
                        visited.append(parent)
                        queue.append((parent, current_weight * weight))


class Stock(Component):
    def update_value(self, new_value: int | float):
        old_value = self.price
        self.price = new_value

        value_difference = new_value - old_value
        self.update_parent_values(value_difference)


class Portfolio(Component):
    def __init__(self, name: str, price_refidx: int, graph: ProxyType):
        super().__init__(name, price_refidx, graph)
        # lists of (normally) ints:
        self.assets = []
        self.weights = []

    @property
    def asset_prices(self) -> ndarray:
        return self.graph.all_prices[self.assets]

    def update_value(self, value_difference: int | float = nan) -> bool:
        """Supports fully recomputing portfolio or incremental update from single new asset price"""
        # print(f"...evaluating {self.name}")
        if not isnan(self.price) and not isnan(value_difference):
            self.price += value_difference
        elif any(isnan(px := self.asset_prices)):
            return False
        else:  # first time value calculated (all component prices are present)
            self.price = dot(px, self.weights)
        return True


class AssetGraph:

    """To represent and implement what can be disconnected subgraphs of stocks and
    (optionally other portfolios) belonging to portfolios"""

    def __init__(self):
        """Adjacency lists (representation) and Nodes (implementation) for later:
            filling (add components, edges) and two-step initialization (creating and linking node instances)"""
        self.stocks = {}      # leaves in a tree-like graph, actual nodes. stocks and portfolio are separated mostly for clarity
        self.portfolios = {}  # non-leaves in a tree-like graph, actual nodes including "roots" (top-level portfolios if needed)
        # intermediate structures, from which graph is later constructed:
        self.adj_list_parents_stocks = {}         # key names and values are parents (portfolios)
        self.adj_list_parents_stock_weights = {}  # identical structure for weights (dicts and values, which are lists, both are ordered in Python)
        self.adj_list_parents_portfolios = {}  # keys are (sub)portfolio names, values are lists of parent portfolios
        self.adj_list_parents_portfolio_weights = {}
        # self.incomplete_stocks = set()  # for lazy initialization of evaluation DAGs (keep track of partial graphs that can be made complete as new prices appear)

    def add_components_from(self, data_provider: Iterable):
        """Interface, e.g. generator (better, lazy), ensures that the graph class is decoupled from the input source,
         e.g. portfolios.csv, or other data read line-by-line, or (non-lazy) in-memory container like List"""
        portfolio_name = ""
        for line_items in data_provider:
            if len(line_items) == 1 or len(line_items[1]) == 0:  # no quantity or empty string
                self.add_component(portfolio_name := line_items[0])
            elif len(line_items) == 2:
                ticker, quantity = line_items
                if (ticker.strip().upper() == "NAME") and \
                   (quantity.strip().upper() == "SHARES"):
                    continue
                if portfolio_name:
                    self.add_component(name=ticker, qty=float(quantity), parent=portfolio_name)
                else:
                    raise ValueError("expected portfolio name before list of components and quantities")
            elif line_items:
                raise AttributeError("expected one or two arguments, not more line items")
            else:
                continue  # to handle or for now skipping empty line or EOF

    def add_component(self, name: str, qty: int | float = None, parent: str | None = None):
        """Only fills adjacency lists, actual initialization of nodes is done later so that each node is created only once"""
        assert (parent is None) ^ (qty is not None), \
            "per example data: stock always belong to some portfolio and have quantity"
        if parent is not None:
            if name in self.adj_list_parents_stocks:
                self.adj_list_parents_stocks[name].append(parent)
                self.adj_list_parents_stock_weights[name].append(qty)  # can be a "subportfolio", not efficient to check here, instead will get reclassifed in self.fix_structure()
            else:
                self.adj_list_parents_stocks[name] = [parent]  # these 2 lines won't be needed for defaultdict implementation
                self.adj_list_parents_stock_weights[name] = [qty]
        else:
            if name not in self.adj_list_parents_portfolios:
                self.adj_list_parents_portfolios[name] = []  # defaultdict can be used as alternative implementation, but requires more changes
                self.adj_list_parents_portfolio_weights[name] = []

    @property
    def merged_view(self) -> tuple:
        """Two adjaency lists: all nodes/components as combined dictionary and respectively all weights """
        return ( ChainMap(self.adj_list_parents_portfolios, self.adj_list_parents_stocks),
                  ChainMap(self.adj_list_parents_portfolio_weights, self.adj_list_parents_stock_weights) )

    def fix_structure(self):
        """ Corrects adjacency lists that were built as data was "read in" (easier to distinguish
        stocks and portfolios on final set of related chunks of data) """
        to_move = [node for node in self.adj_list_parents_stocks if node in self.adj_list_parents_portfolios]
        for node in to_move:
            parents = self.adj_list_parents_stocks.pop(node)
            parent_weights = self.adj_list_parents_stock_weights.pop(node)
            self.adj_list_parents_portfolios[node].extend(parents)
            self.adj_list_parents_portfolio_weights[node].extend(parent_weights)

    def init_components(self):
        """Finalizes adjacency lists, and then creates a single central prices array maintained during valuations,
             and in a Two-step process establishes nodes with edge (direct connectivity) info in them"""
        self.fix_structure()
        self._init_prices()  # create a central prices array and map locating their tickers
        # 2 steps: init all nodes, then "fill info about edges" (parents/children all initialized)
        self._init_nodes()
        self._link_nodes()  # this can be done with a reverse map, instead inverse relations are kept in nodes

    def _init_prices(self):
        self.all_prices = full(len(self.merged_view[0]), nan)  # numpy array for efficient sum, ordered per dict
        # map str tickers to int indices into numpy array.  done for clarity and easier debugging
        self.all_refidx = {ticker: i for i, ticker in enumerate(self.merged_view[0].keys())}

    def _init_nodes(self):
        for name, owners in self.adj_list_parents_stocks.items():
            self.stocks[name] = Stock(name, graph=proxy(self), price_refidx=self.all_refidx[name])
        for name, owners in self.adj_list_parents_portfolios.items():
            self.portfolios[name] = Portfolio(name,
                                              graph=proxy(self),
                                              price_refidx=self.all_refidx[name])

    def _link_nodes(self):
        for name, stock in self.stocks.items():
            for owner, w in zip(self.adj_list_parents_stocks[name], self.adj_list_parents_stock_weights[name]):
                self.portfolios[owner].weights.append(w)
                self.portfolios[owner].assets.append(stock.price_refidx)
        for name, portfolio in self.portfolios.items():
            for owner, w in zip(self.adj_list_parents_portfolios[name], self.adj_list_parents_portfolio_weights[name]):
                self.portfolios[owner].weights.append(w)
                self.portfolios[owner].assets.append(portfolio.price_refidx)
