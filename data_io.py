def read_csv_portfolios_weights(filename):
    """Read portfolio data from file (e.g. CSV) in blocks.
    Each block defines a portfolio.
    Each block starts with a portfolio name, which is followed by the components and weights

    :filename: str or pathlib.Path for file to read data from
    """
    with open(filename, 'r') as file:
        header = next(file).strip().split(',')
        if (header[0].strip().upper() != "NAME") or \
           (header[1].strip().upper() != "SHARES"):
            raise ValueError(f"Header {header} does not match expected format: 'NAME, SHARES'")
        block = []  # to store portfolio chunks (definition: name and components with weights)

        for line in file:
            line = line.strip()
            if not line:  # to handle or, for now, skip empty line or EOF
                continue

            line_items = line.split(',')
            if len(line_items) == 1 or len(line_items[1]) == 0:  # new portfolio block
                if block:  # yield the previous block if it exists
                    yield block
                block = [line_items[0]]  # start a new block with only portfolio name
            elif len(line_items) == 2:   #  or append to existing if read component and weight
                block.append(line_items)
            else:
                raise ValueError(f"expected one or two line items, got: {line}")

        if block:  # at EOF, yield the last block
            yield block


def read_csv_prices(filename):
    with open(filename, 'r') as file:
        header = next(file).strip().split(',')
        if (header[0].strip().upper() != "NAME") or \
           (header[1].strip().upper() != "SHARES"):
            raise ValueError(f"Header {header} does not match expected format: 'NAME, SHARES'")


def write_csv_prices(filename):
    pass