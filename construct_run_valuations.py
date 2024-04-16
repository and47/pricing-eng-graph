from portfolio_tool import AssetGraph

# example with input files
from data_io import read_csv_portfolios_weights, streamin_csv_prices

generator_portfolios = read_csv_portfolios_weights("./hwboa_portf_px/portfolios.csv")

simPortfolio = AssetGraph(stdout=open("out_prices.csv", 'a'))
simPortfolio.add_components_from(generator_portfolios)

simPortfolio.init_components()  # finished defining portfolios


generator_prices = streamin_csv_prices("./hwboa_portf_px/prices.csv")
simPortfolio.update_prices_from(generator_prices)  # streams continuously, press Ctrl-C to stop



# example with manual user input

userPortfolio = AssetGraph()
userPortfolio.add_component('TECH')
userPortfolio.add_component('AAPL', 100, 'TECH')
userPortfolio.add_component('MSFT', 200, 'TECH')
userPortfolio.add_component('NVDA', 300, 'TECH')
userPortfolio.add_component('AUTOS')
userPortfolio.add_component('FORD', 100, 'AUTOS')
userPortfolio.add_component('TSLA', 200, 'AUTOS')
userPortfolio.add_component('BMW', 200, 'AUTOS')
userPortfolio.add_component('INDUSTRIALS')
userPortfolio.add_component('TECH', 2, 'INDUSTRIALS')
userPortfolio.add_component('AUTOS', 3, 'INDUSTRIALS')


userPortfolio.init_components()

userPortfolio.stocks['AAPL'].update_value(173)
userPortfolio.stocks['MSFT'].update_value(425)
userPortfolio.stocks['NVDA'].update_value(880)
userPortfolio.stocks['AAPL'].update_value(174)

userPortfolio.stocks['BMW'].update_value(14.43)
userPortfolio.stocks['FORD'].update_value(36)
userPortfolio.stocks['TSLA'].update_value(510.72)

# Notes
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
# - allowing and not catching cycles in a graph. an alternative implementation with Kahn's algorithm for toposort could have improved that
