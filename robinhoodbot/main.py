import pyotp
import robin_stocks as r
import pandas as pd
import numpy as np
import ta as ta
from pandas.plotting import register_matplotlib_converters
from ta import *
from misc import *
from tradingstats import *
from config import *

#Log in to Robinhood
#Put your username and password in a config.py file in the same directory (see sample file)
totp  = pyotp.TOTP(rh_2fa_code).now()
login = r.login(rh_username,rh_password, totp)

#Safe divide by zero division function
def safe_division(n, d):
    return n / d if d else 0

def get_spy_symbols():
    """
    Returns: the symbol for each stock in the S&P 500 as a list of strings
    """
    symbols = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol']
    return list(symbols.values.flatten())

def get_watchlist_symbols():
    """
    Returns: the symbol for each stock in your watchlist as a list of strings
    """
    my_list_names = []
    symbols = []
    for name in r.get_all_watchlists(info='name'):
        my_list_names.append(name)
    for name in my_list_names:
        list = r.get_watchlist_by_name(name)
        for item in list:
            instrument_data = r.get_instrument_by_url(item.get('instrument'))
            symbol = instrument_data['symbol']
            symbols.append(symbol)
    return symbols

def get_portfolio_symbols():
    """
    Returns: the symbol for each stock in your portfolio as a list of strings
    """
    symbols = []
    holdings_data = r.get_open_stock_positions()
    for item in holdings_data:
        if not item:
            continue
        instrument_data = r.get_instrument_by_url(item.get('instrument'))
        symbol = instrument_data['symbol']
        symbols.append(symbol)
    return symbols

def get_position_creation_date(symbol, holdings_data):
    """Returns the time at which we bought a certain stock in our portfolio

    Args:
        symbol(str): Symbol of the stock that we are trying to figure out when it was bought
        holdings_data(dict): dict returned by r.get_open_stock_positions()

    Returns:
        A string containing the date and time the stock was bought, or "Not found" otherwise
    """
    instrument = r.get_instruments_by_symbols(symbol)
    url = instrument[0].get('url')
    for dict in holdings_data:
        if(dict.get('instrument') == url):
            return dict.get('created_at')
    return "Not found"

def get_modified_holdings():
    """ Retrieves the same dictionary as r.build_holdings, but includes data about
        when the stock was purchased, which is useful for the read_trade_history() method
        in tradingstats.py

    Returns:
        the same dict from r.build_holdings, but with an extra key-value pair for each
        position you have, which is 'bought_at': (the time the stock was purchased)
    """
    holdings = r.build_holdings()
    holdings_data = r.get_open_stock_positions()
    for symbol, dict in holdings.items():
        bought_at = get_position_creation_date(symbol, holdings_data)
        bought_at = str(pd.to_datetime(bought_at))
        holdings[symbol].update({'bought_at': bought_at})
    return holdings

def golden_cross(stockTicker, n1, n2, direction=""):
    """Determine if a golden/death cross has occured for a specified stock in the last X trading days

    Args:
        stockTicker(str): Symbol of the stock we're querying
        n1(int): Specifies the short-term indicator as an X-day moving average.
        n2(int): Specifies the long-term indicator as an X-day moving average.
                 (n1 should be smaller than n2 to produce meaningful results, e.g n1=50, n2=200)
        direction(str): "above" if we are searching for an upwards cross, "below" if we are searching for a downwaords cross. Optional, used for printing purposes

    Returns:
        1 if the short-term indicator crosses above the long-term one
        0 if the short-term indicator crosses below the long-term one

        price(float): last listed close price
    """
    history = get_historicals(stockTicker)
    closingPrices = []
    dates = []
    for item in history:
        closingPrices.append(float(item['close_price']))
        dates.append(item['begins_at'])
    price = pd.Series(closingPrices)
    dates = pd.Series(dates)
    dates = pd.to_datetime(dates)
    ema1 = ta.trend.EMAIndicator(price, int(n1)).ema_indicator()
    ema2 = ta.trend.EMAIndicator(price, int(n2)).ema_indicator()
    if plot:
        show_plot(price, ema1, ema2, dates, symbol=stockTicker, label1=str(n1)+" day EMA", label2=str(n2)+" day EMA")
    return ema1.iat[-1] > ema2.iat[-1],  closingPrices[len(closingPrices) - 1]

def get_rsi(symbol, days):
    """Determine the relative strength index for a specified stock in the last X trading days

    Args:
        symbol(str): Symbol of the stock we're querying
        days(int): Specifies the maximum number of days that the cross can occur by

    Returns:
        rsi(float): Relative strength index value for a specified stock in the last X trading days
    """
    history = get_historicals(symbol)
    closingPrices = [ float(item['close_price']) for item in history ]
    price = pd.Series(closingPrices)
    rsi = ta.momentum.RSIIndicator(close=price, window=int(days), fillna=False).rsi()
    return rsi.iat[-1]

def get_macd(symbol):
    """Determine the Moving Average Convergence/Divergence for a specified stock 

    Args:
        symbol(str): Symbol of the stock we're querying

    Returns:
        rsi(float): Moving Average Convergence/Divergence value for a specified stock 
    """
    history = get_historicals(symbol)
    closingPrices = [ float(item['close_price']) for item in history ]
    price = pd.Series(closingPrices)
    macd = ta.trend.MACD(price).macd_diff()
    return macd.iat[-1]

def get_buy_rating(symbol):
    """Determine the listed investor rating for a specified stock 

    Args:
        symbol(str): Symbol of the stock we're querying

    Returns:
        rating(int): 0-100 rating of a particular stock 
    """ 
    ratings = r.get_ratings(symbol=symbol)['summary']
    
    if ratings:
        return ratings['num_buy_ratings'] / (ratings['num_buy_ratings'] + ratings['num_hold_ratings'] + ratings['num_sell_ratings']) * 100
    
    return 0

def sell_holdings(symbol, holdings_data):
    """ Place an order to sell all holdings of a stock.

    Args:
        symbol(str): Symbol of the stock we want to sell
        holdings_data(dict): dict obtained from get_modified_holdings() method
    """
    shares_owned = int(float(holdings_data[symbol].get("quantity")))
    if not debug:
        r.order_sell_market(symbol, shares_owned)
    print("####### Selling " + str(shares_owned) + " shares of " + symbol + " #######")

def buy_holdings(potential_buys, profile_data, holdings_data):
    """ Places orders to buy holdings of stocks. This method will try to order
        an appropriate amount of shares such that your holdings of the stock will
        roughly match the average for the rest of your portfoilio. If the share
        price is too high considering the rest of your holdings and the amount of
        buying power in your account, it will not order any shares.

    Args:
        potential_buys(list): List of strings, the strings are the symbols of stocks we want to buy
        symbol(str): Symbol of the stock we want to sell
        holdings_data(dict): dict obtained from r.build_holdings() or get_modified_holdings() method
    """
    cash = float(profile_data.get('cash'))
    portfolio_value = float(profile_data.get('equity')) - cash
    ideal_position_size = (safe_division(portfolio_value, len(holdings_data))+cash/len(potential_buys))/(2 * len(potential_buys))
    prices = r.get_latest_price(potential_buys)
    for i in range(0, len(potential_buys)):
        stock_price = float(prices[i])
        if(ideal_position_size < stock_price < ideal_position_size*1.5):
            num_shares = int(ideal_position_size*1.5/stock_price)
        elif (stock_price < ideal_position_size):
            num_shares = int(ideal_position_size/stock_price)
        else:
            print("####### Tried buying shares of " + potential_buys[i] + ", but not enough buying power to do so#######")
            break
        print("####### Buying " + str(num_shares) + " shares of " + potential_buys[i] + " #######")
        if not debug:
            r.order_buy_market(potential_buys[i], num_shares)

def scan_stocks():
    """ The main method. Sells stocks in your portfolio if their 50 day moving average crosses
        below the 200 day, and buys stocks in your watchlist if the opposite happens.

        ###############################################################################################
        WARNING: Comment out the sell_holdings and buy_holdings lines if you don't actually want to execute the trade.
        ###############################################################################################

        If you sell a stock, this updates tradehistory.txt with information about the position,
        how much you've earned/lost, etc.
    """
    if debug:
        print("----- DEBUG MODE -----\n")
    print("----- Starting scan... -----\n")
    register_matplotlib_converters()
    spy_symbols = get_spy_symbols()
    portfolio_symbols = get_portfolio_symbols()
    holdings_data = get_modified_holdings()
    potential_buys = []
    sells = []
    stock_data = []
    print("Current Portfolio: " + str(portfolio_symbols) + "\n")
    # print("Current Watchlist: " + str(watchlist_symbols) + "\n")
    print("----- Scanning portfolio for stocks to sell -----\n")
    print()
    print("PORTFOLIO")
    print("-------------------")
    print()
    print ("{}\t{}\t\t{}\t{}\t{}\t{}".format('SYMBOL', 'PRICE', 'RSI', 'MACD', 'RATING', 'EMA')) 
    print()
    for symbol in portfolio_symbols:
        cross, price = golden_cross(symbol, n1=50, n2=200, direction="below")
        data = {'symbol': symbol, 'price': price, 'cross': cross, 'rsi': get_rsi(symbol=symbol, days=14), 'macd': get_macd(symbol=symbol), 'buy_rating': get_buy_rating(symbol=symbol)}
        stock_data.append(data)
        print ("{}\t${:.2f}\t\t{}\t{}\t{}\t{}".format(data['symbol'], data['price'], rsi_to_str(data['rsi']), macd_to_str(data['macd']), rating_to_str(data['buy_rating']), cross_to_str(data['cross'])))
        if(cross == False):
            sell_holdings(symbol, holdings_data)
            sells.append(symbol)
    profile_data = r.build_user_profile()
    print("\n----- Scanning S&P 500 for stocks to buy -----\n")
    for symbol in spy_symbols:
        if(symbol not in portfolio_symbols):
            cross, price = golden_cross(symbol, n1=50, n2=200, direction="above")
            stock_data.append({'symbol': symbol, 'price': price, 'cross': cross, 'rsi': get_rsi(symbol=symbol, days=14), 'macd': get_macd(symbol=symbol), 'buy_rating': get_buy_rating(symbol=symbol)})
            if(cross == True):
                potential_buys.append(symbol)
    if(len(potential_buys) > 0):
        buy_holdings(potential_buys, profile_data, holdings_data)
    if(len(sells) > 0):
        update_trade_history(sells, holdings_data, "tradehistory.txt")
    print("----- Scan over -----\n")
    print_table(stock_data)
    if debug:
        print("----- DEBUG MODE -----\n")

#execute the scan
scan_stocks()
