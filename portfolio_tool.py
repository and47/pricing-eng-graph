import sys
from collections import ChainMap, deque
from weakref import proxy, ProxyType

from numpy import nan, isnan, array, ndarray, full, dot, zeros
from typing import Iterable
from abc import ABCMeta, abstractmethod


class Component(metaclass=ABCMeta):
    """Composite design pattern to universally represent graph Nodes (whether stocks or portfolios)"""
    def __init__(self, name: str, idx: int, price_refidx: int, graph: ProxyType):
        self.name = name
        self.id = idx  # unlike price_refidx, this id (index) is separate portfolio or stock (both start from 0s)
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
            print(self, file=self.graph.stdout, flush=True)

    def __str__(self):
        return f"{self.name},{self.price}"

    @abstractmethod
    def update_value(self):
        pass

    def update_parent_values(self):
        """BFS (bottom-up) price updates for only affected portfolios and only if all input prices are present
        This is implementation of 1st approach, traversal on every stock price update.
        See `update_owners_deltas` for 2nd approach, where value_difference is used for incremental update using pre-
         computed factors (traversal is done at `AssetGraph.init_components`). Also, see `AssetGraph.stock_deltas`).
        In multi-processing env can lock the tree being updated and only allow updates on disconnected subgraphs"""

        visited = [self.name]  # BFS visited nodes. name, weight (placeholder for 0th node)
        queue = deque([self.name])  # BFS queue without weights
        status = True  # early stop for BFS (affected nodes after a node that can't be priced)

        while queue:
            node = queue.popleft()  # collections.deque.popleft() is faster than list.pop(0)
            if node != self.name:  # evaluate parent portfolios using cumulative (product of prior) weights:
                # incremental update abandoned after own test cases (both direct and indirect ownership)
                status = self.graph.portfolios[node].update_value()  # value_difference is used in approach 2, see help
            if status:
                for parent in self.graph.merged_view[0][node]:  # over stock/portfolio owners
                    if parent not in visited:
                        visited.append(parent)
                        queue.append(parent)

    def update_owners_deltas(self):
        """BFS (bottom-up) delta (incremental) updates for only affected portfolios.
        No early stopping unlike `self.update_parent_values`. """
        visited = [self.name]  # BFS visited nodes. name, weight (placeholder for 0th node)
        queue = deque([(self.name, 1)])  # double-ended queue for BFS with weights (cumulative product along the ownership path)

        stock_name, stock_id = self.name, self.id  # name and index (used for navigation)
        while queue:
            node_name, current_weight = queue.popleft()  # collections.deque.popleft() is faster than list.pop(0)
            if node_name != stock_name:  # calculate parent portfolio delta as cumulative (product of prior) weights:
                self.graph.portfolios[node_name].set_delta(stock_id, delta=current_weight)
            for parent, weight in zip(self.graph.merged_view[0][node_name],
                                      self.graph.merged_view[1][node_name]):
                if parent not in visited:  # this works as between 2 layers there's only 1 edge, but stock can be owned
                    visited.append(parent)  # ... both directly and indirectly at the same time (by same portfolio)
                    queue.append((parent, current_weight * weight))


class Stock(Component):
    def update_value(self, new_value: int | float):
        old_value = self.price
        self.price = new_value

        value_difference = new_value - old_value
        is_first_price = isnan(value_difference)
        stock_id = self.id
        if self.graph.stock_deltas is not None and stock_id < self.graph.stock_deltas.shape[1]:  # approach 2
            # efficiently update only affected portfolios using deltas without traversal (done at init stage)
            for portfolio_id, delta_s in enumerate(self.graph.stock_deltas[:, stock_id]):
                if delta_s:  # !=0 => affected portfolio
                    portfolio_name = list(self.graph.portfolios.keys())[portfolio_id]
                    if is_first_price:
                        self.graph.portfolios[portfolio_name].n_px_to_value -= 1
                        self.graph.portfolios[portfolio_name].update_value(self.price * delta_s)
                    else:
                        self.graph.portfolios[portfolio_name].update_value(value_difference * delta_s)
        else:  # approach 1
            self.update_parent_values()


class Portfolio(Component):
    def __init__(self, name: str, idx: int, price_refidx: int, graph: ProxyType):
        super().__init__(name, idx, price_refidx, graph)
        # lists of (normally) ints:
        self.assets = []  # all
        self.weights = []
        self.n_px_to_value = 0  # stocks prices counter: number of ultimate underlying price required to value self

    @property
    def asset_prices(self) -> ndarray:
        return self.graph.all_prices[self.assets]

    def update_value(self, value_difference: int | float = nan) -> bool:
        """
        Evaluate portfolio if possible. Supports fully recomputing portfolio value or an
        incremental update from a single new asset price (value_difference already is weight multiplied).
        :return: bool True if successful valuation or False if lacks one or more stock prices
        """
        # print(f"...evaluating {self.name}")
        if not isnan(self.price) and not isnan(value_difference):
            self.price += value_difference
        elif self.graph.stock_deltas is None and any(isnan(self.asset_prices)):  # O(n) in 1st valuation approach
            return False
        elif self.n_px_to_value > 0:  # O(1) in 2nd approach (single traversal)
            return False
        else:  # first time value calculated (all component prices are present)
            self.price = dot(self.asset_prices, self.weights)
        return True

    def set_delta(self, stock_id: int, delta: int | float = nan) -> None:
        """Update cumulative (product) delta of the ultimate underlying stock"""
        # print(f"...evaluating {self.name}")
        # update "total" delta: from 0 or increment existing delta (via one portfolio path) with new one (via another ownership path)
        portfolio_id = self.id
        if self.graph.stock_deltas[portfolio_id, stock_id] == 0:
            self.n_px_to_value += 1  # new stock (ultimate underlying) portfolio depends on
        self.graph.stock_deltas[portfolio_id, stock_id] += delta  # portfolios in rows, price_refidx == P deltas rindex


class AssetGraph:

    """To represent and implement what can be disconnected subgraphs of stocks and
    (optionally other portfolios) belonging to portfolios"""

    def __init__(self, stdout=sys.stdout):
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
        self.stdout = stdout  # work-around to print (append) to file, defaults to console
        self.stock_deltas = None  # see `self.init_components`

    def add_components_from(self, data_provider: Iterable):
        """Interface, e.g. generator (better, lazy), ensures that the graph class is decoupled from the input source,
         e.g. portfolios.csv, or other data read line-by-line, or (non-lazy) in-memory container like List.
         For data integrity, portfolio data is expected in blocks (combining info on each single portfolio)"""

        for portfolio_block in data_provider:
            if isinstance(portfolio_block[0], str):  # a single string with portfolio name defines new block
                self.add_component(portfolio_name := portfolio_block[0])
            else:
                raise ValueError("expected portfolio name at the start (before list of components and quantities)")

            for line_items in portfolio_block[1:]:  # process the rest of the items in the block
                if len(line_items) == 2:
                    ticker, quantity = line_items
                    if portfolio_name:
                        self.add_component(name=ticker, qty=float(quantity), parent=portfolio_name)
                    else:
                        raise ValueError(f"Invalid portfolio name, {portfolio_name}")  # check for empty string
                else:
                    raise ValueError(f"Line items for {portfolio_name=} do not match expected format. " + \
                                     f"Expected Component and Quantity, got: {line_items}")

    def add_component(self, name: str, qty: int | float = None, parent: str | None = None):
        """Only fills adjacency lists, actual initialization of nodes is done later so that each node is created only once"""
        assert (parent is None) ^ (qty is not None), \
            "per example data: stock always belong to some portfolio and have quantity"
        if parent is not None:
            if name in self.adj_list_parents_stocks:  # can be improved to treat duplicate info (repeated edge)
                self.adj_list_parents_stocks[name].append(parent)
                self.adj_list_parents_stock_weights[name].append(qty)  # can be a "subportfolio", not efficient to check here, instead will get reclassifed in self.fix_structure()
            else:
                self.adj_list_parents_stocks[name] = [parent]  # these 2 lines won't be needed for defaultdict implementation
                self.adj_list_parents_stock_weights[name] = [qty]
        else:
            if name not in self.adj_list_parents_portfolios:
                self.adj_list_parents_portfolios[name] = []  # defaultdict can be used as alternative implementation, but requires more changes
                self.adj_list_parents_portfolio_weights[name] = []

    def update_prices_from(self, data_provider: Iterable):
        """Interface, e.g. generator (better, lazy), ensures that the graph class is decoupled from the input source,
         e.g. prices.csv, or other data streamed in line-by-line, or (non-lazy) in-memory container like List."""
        for (ticker, price) in data_provider:
            self.stocks[ticker].update_value(float(price))

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

    def init_components(self, est_risk_factors: bool | None = False):
        """Finalizes adjacency lists, and then creates a single central prices array maintained during valuations,
             and in a Two-step process establishes nodes with edge (direct connectivity) info in them.
        :param est_risk_factors: establish risk factors, i.e. delta to ultimate underlying stocks by performing graph
         traversal to leave nodes and creating an array of deltas for each portfolio. Aka 2nd valuation approach.
        """
        self.fix_structure()
        self._init_prices()  # create a central prices array and map locating their tickers
        # 2 steps: init all nodes, then "fill info about edges" (parents/children all initialized)
        self._init_nodes()
        self._link_nodes()  # this can be done with a reverse map, instead inverse relations are kept in nodes
        if est_risk_factors:
            self.stock_deltas = zeros(shape=(len(self.portfolios), len(self.stocks)), dtype=float)
            for stock_node in self.stocks.values():
                stock_node.update_owners_deltas()

    def _init_prices(self):
        self.all_prices = full(len(self.merged_view[0]), nan)  # numpy array for efficient sum, ordered per dict
        # map str tickers to int indices into numpy array.  done for clarity and easier debugging
        self.all_refidx = {ticker: i for i, ticker in enumerate(self.merged_view[0].keys())}

    def _init_nodes(self):
        for i, (name, owners) in enumerate(self.adj_list_parents_stocks.items()):
            self.stocks[name] = Stock(name, idx=i, graph=proxy(self), price_refidx=self.all_refidx[name])
        for i, (name, owners) in enumerate(self.adj_list_parents_portfolios.items()):
            self.portfolios[name] = Portfolio(name, idx=i, graph=proxy(self), price_refidx=self.all_refidx[name])

    def _link_nodes(self):
        for name, stock in self.stocks.items():
            for owner, w in zip(self.adj_list_parents_stocks[name], self.adj_list_parents_stock_weights[name]):
                self.portfolios[owner].weights.append(w)
                self.portfolios[owner].assets.append(stock.price_refidx)
        for name, portfolio in self.portfolios.items():
            for owner, w in zip(self.adj_list_parents_portfolios[name], self.adj_list_parents_portfolio_weights[name]):
                self.portfolios[owner].weights.append(w)
                self.portfolios[owner].assets.append(portfolio.price_refidx)
