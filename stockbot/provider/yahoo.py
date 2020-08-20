import logging
import requests
import urllib.parse
from datetime import datetime

from stockbot.provider.base import BaseQuoteService

LOGGER = logging.getLogger(__name__)


class YahooFallbackQuote(object):

    def __init__(self, *args, **kwargs):
        pass

    def __str__(self):
        return "Didn't find anything"

    def is_empty(self):
        return False

    def is_fresh(self):
        return False


class YahooQuote(object):

    def __init__(self, o):
        self.result = o["optionChain"]["result"][0]
        if "regularMarketTime" in self.result["quote"]:
            self.timestamp = datetime.fromtimestamp(int(self.result["quote"]["regularMarketTime"]))
            self.timestamp_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        else:
            self.timestamp = None
            self.timestamp_str = "unknown"

    def __str__(self):
        return "Name: {name}, Price: {price}, Low Price: {low_price}, High Price: {high_price}, Percent Change 1 Day: {p1d}, Market: {market}, Update Time: {update_time}".format(
            name=self.result["quote"]["shortName"],
            price=self.result["quote"]["regularMarketPrice"],
            low_price=self.result["quote"]["regularMarketDayLow"],
            high_price=self.result["quote"]["regularMarketDayHigh"],
            p1d=self.result["quote"]["regularMarketChangePercent"],
            market=self.result["quote"]["market"],
            update_time=self.timestamp_str
        )

    def is_empty(self):
        return False

    def is_fresh(self):
        if self.timestamp is None:
            return False
        return (datetime.now() - self.timestamp).total_seconds() < 16 * 60


class YahooSearchResult(object):

    def __init__(self, o):
        self.o = o

    def get_tickers(self):
        return [x["symbol"] for x in self.o["quotes"] if "symbol" in x]

    def is_empty(self):
        return not ("quotes" in self.o and len(self.o["quotes"]) > 0)


class YahooQueryService(BaseQuoteService):
    # search results probably don't change that much so cache them
    search_cache = {}

    def __init__(self, *args, **kwargs):
        pass

    def get_quote(self, ticker):
        search_result = self.search(ticker)
        if not search_result.is_empty():
            t = search_result.get_tickers()[0]
            response = requests.get("https://query1.finance.yahoo.com/v7/finance/options/{t}".format(t=t))
            response.raise_for_status()
            return YahooQuote(response.json())
        else:
            return YahooFallbackQuote()

    def search(self, query):
        query_encoded = urllib.parse.quote(query)
        response = requests.get(
            'https://query2.finance.yahoo.com/v1/finance/search?q='
            '{query}&lang=en-US&region=US&quotesCount=1&newsCount=0&enableFuzzyQuery=false&quotesQueryId'
            '=tss_match_phrase_query&multiQuoteQueryId=multi_quote_single_token_query&newsQueryId=news_cie_vespa'
            '&enableCb=true&enableNavLinks=true&enableEnhancedTrivialQuery=true'.format(query=query_encoded))
        response.raise_for_status()
        return YahooSearchResult(response.json())
