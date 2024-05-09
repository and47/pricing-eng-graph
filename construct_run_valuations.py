# tested with 3.10.14

from portfolio_tool import AssetGraph

# example with input files
from data_io import read_csv_portfolios_weights, streamin_csv_prices

generator_portfolios = read_csv_portfolios_weights("./portfolios.csv")

simUniverse = AssetGraph(stdout=open("portfolio_prices.csv", 'a'))
simUniverse.add_components_from(generator_portfolios)

simUniverse.init_components(est_risk_factors=True)  # finished defining portfolios
# simUniverse.init_components()  # slower alternative, defaulting to est_risk_factors=False


generator_prices = streamin_csv_prices("./prices.csv")
simUniverse.update_prices_from(generator_prices)  # streams continuously, press Ctrl-C to stop



# example with manual user input of asset universe

userUniverse = AssetGraph()
userUniverse.add_component('TECH')
userUniverse.add_component('AAPL', 100, 'TECH')
userUniverse.add_component('MSFT', 200, 'TECH')
userUniverse.add_component('NVDA', 300, 'TECH')
userUniverse.add_component('AUTOS')
userUniverse.add_component('FORD', 100, 'AUTOS')
userUniverse.add_component('TSLA', 200, 'AUTOS')
userUniverse.add_component('BMW', 200, 'AUTOS')
userUniverse.add_component('INDUSTRIALS')
userUniverse.add_component('TECH', 2, 'INDUSTRIALS')
userUniverse.add_component('AUTOS', 3, 'INDUSTRIALS')


userUniverse.init_components(est_risk_factors=True)
# userUniverse.init_components()

userUniverse.stocks['AAPL'].update_value(173)
userUniverse.stocks['MSFT'].update_value(425)
userUniverse.stocks['NVDA'].update_value(880)
userUniverse.stocks['AAPL'].update_value(174)

userUniverse.stocks['BMW'].update_value(14.43)
userUniverse.stocks['FORD'].update_value(36)
userUniverse.stocks['TSLA'].update_value(510.72)
