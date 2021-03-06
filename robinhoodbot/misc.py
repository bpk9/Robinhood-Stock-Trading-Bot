import robin_stocks as r
import matplotlib.pyplot as plt
import matplotlib.ticker as plticker
import numpy as np
from termcolor import colored

# cached historicals
historicals = {}

def cross_to_str(cross):
    """Converts cross int to readable string

    Args:
        cross(bool)

    Returns:
        cross_str(string)
    """
    if cross == True:
        return colored("Bullish", 'green')
    else:
        return colored("Bearish", 'red')

def rsi_to_str(rsi):
    """Converts rsi float to readable string

    Args:
        rsi(float)

    Returns:
        rsi_str(string)
    """
    if rsi <= 30:
        return colored(str('%.2f' % rsi), 'green')
    elif rsi >= 70:
        return colored(str('%.2f' % rsi), 'red')
    else:
        return str('%.2f' % rsi)

def macd_to_str(macd):
    """Converts macd float to readable string

    Args:
        macd(float)

    Returns:
        macd_str(string)
    """
    if macd > 0:
        return colored(str('%.2f' % macd), 'green')
    else:
        return colored(str('%.2f' % macd), 'red')

def rating_to_str(rating):
    """Converts rating float to readable string

    Args:
        rating(float)

    Returns:
        rating_str(string)
    """
    if rating >= 70:
        return colored(str('%.0f' % rating), 'green')
    else:
        return colored(str('%.0f' % rating), 'red')

def print_table(stock_data):
    """Prints a table of all stock symbols and key indicators

    Args:
        stock_data(dict)

    Returns:
        None
    """
    # print ("{}\t{}\t\t{}\t{}\t{}\t{}".format('SYMBOL', 'PRICE', 'RSI', 'MACD', 'RATING', 'EMA')) 

    potential_stocks = []

    for data in stock_data: 
        # print ("{}\t${:.2f}\t\t{}\t{}\t{}\t{}".format(data['symbol'], data['price'], rsi_to_str(data['rsi']), macd_to_str(data['macd']), rating_to_str(data['buy_rating']), cross_to_str(data['cross'])))
        if (data['rsi'] < 45) and (data['price'] < 200) and (data['macd'] > -1)  and (data['buy_rating'] >= 70) and (data['cross'] == True):
            potential_stocks.append(data)

    print()
    print("STOCKS TO CHECK OUT")
    print("-------------------")
    print()
    print ("{}\t{}\t\t{}\t{}\t{}\t{}".format('SYMBOL', 'PRICE', 'RSI', 'MACD', 'RATING', 'EMA')) 
    print()

    for data in potential_stocks:
        print ("{}\t${:.2f}\t\t{}\t{}\t{}\t{}".format(data['symbol'], data['price'], rsi_to_str(data['rsi']), macd_to_str(data['macd']), rating_to_str(data['buy_rating']), cross_to_str(data['cross'])))

def show_plot(price, firstIndicator, secondIndicator, dates, symbol="", label1="", label2=""):
    """Displays a chart of the price and indicators for a stock

    Args:
        price(Pandas series): Series containing a stock's prices
        firstIndicator(Pandas series): Series containing a technical indicator, such as 50-day moving average
        secondIndicator(Pandas series): Series containing a technical indicator, such as 200-day moving average
        dates(Pandas series): Series containing the dates that correspond to the prices and indicators
        label1(str): Chart label of the first technical indicator
        label2(str): Chart label of the first technical indicator

    Returns:
        None
    """
    plt.figure(figsize=(10,5))
    plt.title(symbol)
    plt.plot(dates, price, label="Closing prices")
    plt.plot(dates, firstIndicator, label=label1)
    plt.plot(dates, secondIndicator, label=label2)
    plt.yticks(np.arange(price.min(), price.max(), step=((price.max()-price.min())/15.0)))
    plt.legend()
    plt.show()

def get_equity_data():
    """Displays a pie chart of your portfolio holdings
    """
    holdings_data = r.build_holdings()
    equity_data = {}
    for key, value in holdings_data.items():
        equity_data[key] = {}
        equity_data[key][name] = value.get('name')
        equity_data[key][percentage] = value.get("percentage")
        equity_data[key][type]
    fig1, ax1 = plt.subplots()
    ax1.pie(equities, labels=labels, autopct='%1.1f%%',
            shadow=True, startangle=90)
    ax1.axis('equal')
    plt.show()

def get_historicals(symbol):
    """Returns the time at which we bought a certain stock in our portfolio

    Args:
        symbol(str): Symbol of the stock that we are trying to figure out when it was bought
        holdings_data(dict): dict returned by r.get_open_stock_positions()

    Returns:
        A string containing the date and time the stock was bought, or "Not found" otherwise
    """
    if symbol not in historicals.keys():
        historicals[symbol] = r.get_historicals(symbol, span='year', bounds='regular')
        # print("Fetched historicals for: {}".format(symbol))
    return historicals[symbol]