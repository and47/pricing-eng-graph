from portfolio_tool import AssetGraph

un = AssetGraph()
un.add_component('TECH')
un.add_component('AAPL', 100, 'TECH')
un.add_component('MSFT', 200, 'TECH')
un.add_component('NVDA', 300, 'TECH')
un.add_component('AUTOS')
un.add_component('FORD', 100, 'AUTOS')
un.add_component('TSLA', 200, 'AUTOS')
un.add_component('BMW', 200, 'AUTOS')
un.add_component('INDUSTRIALS')
un.add_component('TECH', 2, 'INDUSTRIALS')
un.add_component('AUTOS', 3, 'INDUSTRIALS')

# first naive solution produces intermediate result before correct last one
un.add_component('AAPL2')
un.add_component('AAPL', 2, 'AAPL2')
un.add_component('AAPL4')
un.add_component('AAPL', 4, 'AAPL4')
un.add_component('AAPL16')
un.add_component('AAPL2', 4, 'AAPL16')
un.add_component('AAPL4', 2, 'AAPL16')

un.merged_view

un.fix_structure()
un.init_components()

un.stocks['AAPL'].update_value(173)
un.stocks['AAPL'].update_value(174)  # prints AAPL16 twice, only 2nd is correct

# need topo-sort or bfs logic not my dfs (with early stop) is still doing 1 redundant step/attempt
# but topo-sort is expensive to recompute, so cache it?
# also, reduce by excluding inactive nodes, e.g. if MSFT=nan, do not attempty value TECH
# in a way, after pricing MSFT, add TECH as "viable to value" -- add to graph?
# if old price was nan -- enable node

un.merged_view()

un.fix_structure()
un.init_components()

un.stocks['AAPL'].update_value(173)
un.stocks['MSFT'].update_value(425)
un.stocks['NVDA'].update_value(880)
un.stocks['AAPL'].update_value(174)

un.stocks['BMW'].update_value(14.43)
un.stocks['FORD'].update_value(36)
un.stocks['TSLA'].update_value(510.72)

un.add_component('TSLA2x')
un.add_component('ULTRA')
un.add_component('TSLA', 2, 'TSLA2x')
un.add_component('TSLA2x', 10, 'ULTRA')
un.add_component('AAPL2', 5, 'ULTRA')
un.add_component('TECH', 0.5, 'ULTRA')

