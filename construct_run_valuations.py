

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


un.merged_view()

un.fix_structure()
un.init_components()

un.stocks['AAPL'].update_value(173)
un.stocks['MSFT'].update_value(425)
un.stocks['NVDA'].update_value(880)
un.stocks['AAPL'].update_value(174)
