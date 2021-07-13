import logging
import requests
import urllib.parse
from datetime import datetime

from stockbot.provider.base import BaseQuoteService, BaseQuote

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


class YahooQuote(BaseQuote):

    def __init__(self, o):
        for k, v in o["optionChain"]["result"][0]["quote"].items():
            setattr(self, k, v)
        if self.regularMarketTime == "N/A":
            self.timestamp = None
            self.timestamp_str = "unknown"
        else:
            self.timestamp = datetime.fromtimestamp(int(self.regularMarketTime))
            self.timestamp_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        self.is_pre_market = self.marketState == "PRE"

        self.fields = [
            ["Name", self.shortName],
            ["Price", self.regularMarketPrice],
            ["Low Price", self.regularMarketDayLow],
            ["High Price", self.regularMarketDayHigh],
            ["Percent Change 1 Day", self.regularMarketChangePercent]
        ]
        if self.is_pre_market:
            self.fields.extend([
                ["Price Pre Market", self.preMarketPrice],
                ["Percent Change Pre Market", self.preMarketChangePercent]
            ])
        self.fields.extend([
            ["Market", self.market],
            ["Update Time", self.timestamp_str]
        ])

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
        return not (
                "quotes" in self.o and
                len(self.o["quotes"]) > 0 and
                any([True for x in self.o["quotes"] if "symbol" in x])
        )


class YahooQueryService(BaseQuoteService):
    # search results probably don't change that much so cache them
    search_cache = {}

    headers = {
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }

    def __init__(self, *args, **kwargs):
        pass

    def get_quote(self, ticker):
        search_result = self.search(ticker)
        if not search_result.is_empty():
            t = search_result.get_tickers()[0]
            response = requests.get("https://query1.finance.yahoo.com/v7/finance/options/{t}".format(t=t),
                                    headers=self.headers)
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
            '&enableCb=true&enableNavLinks=true&enableEnhancedTrivialQuery=true'.format(query=query_encoded),
            headers=self.headers)
        response.raise_for_status()
        return YahooSearchResult(response.json())
