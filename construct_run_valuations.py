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


un.merged_view
un.init_components()
un.merged_view


un.stocks['AAPL'].update_value(173)
un.stocks['AAPL'].update_value(174)


un.stocks['AAPL'].update_value(173)
un.stocks['MSFT'].update_value(425)
un.stocks['NVDA'].update_value(880)
un.stocks['AAPL'].update_value(174)

un.stocks['BMW'].update_value(14.43)
un.stocks['FORD'].update_value(36)
un.stocks['TSLA'].update_value(510.72)

# - successfully tested on thousands of portfolios
# - generators: - reading from CSV can easily be replaced with other source of sequential IO
#               - do not fill memory, process more on the fly, more pythonic
#               - can e.g. read portfolio definitions until all initial ones are defined, or read prices until all stock appear at least once, or read from the end (for most recent data)


# limitations:
# - allows any float value (not limited to e.g. cents, 2 digits after decimal point)
# - no caching and certain cases failed my incremental update functionality, so it was disabled
# - BFS still makes 1-attempt that in some scenario (too many of updates of same price) could have been cached
#   - topological sort could have been used and updated upon "activation" of new nodes (akin to de-activating part of graph, for which there are no prices)
# - could have used observer design pattern, making further use of weakref, with added benefit of more dynamic (during use) of portfolio definitions, e.g. portfolio removal, etc.
# - not required by the task, but could have allowed for some prices may be known at a stage of portfolio definition


def read_lines(filename):
    with open(filename, 'r') as file:
        for line in file:
            yield line.strip().split(',')

my_gen_csv = read_lines('./hwboa_portf_px/portfolios.csv')

un2 = AssetGraph()
un2.add_components_from(my_gen_csv)
un2.merged_view

un2.init_components()
un2.merged_view

un2.stocks['AAPL'].update_value(173)
un2.stocks['MSFT'].update_value(425)
un2.stocks['NVDA'].update_value(880)
un2.stocks['AAPL'].update_value(174)
