import logging
import requests
import urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup

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
            ["Chart", "https://finance.yahoo.com/chart/{}".format(urllib.parse.quote_plus(self.symbol))],
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

    cookies = {}
    crumb = None

    def __init__(self, *args, **kwargs):
        pass

    def get_quote(self, ticker):
        search_result = self.search(ticker)
        if not search_result.is_empty():
            t = search_result.get_tickers()[0]
            response = self._get_with_cookie_refresh("https://query2.finance.yahoo.com/v7/finance/options/{t}".format(
                t=t))
            response.raise_for_status()
            return YahooQuote(response.json())
        else:
            print(search_result.o)
            return YahooFallbackQuote()

    def search(self, query):
        query_encoded = urllib.parse.quote(query)
        if query_encoded not in self.search_cache:
            response = requests.get('https://query2.finance.yahoo.com/v1/finance/search', params={
                "q": query_encoded,
                "lang": "en-US",
                "region": "US",
                "quotesCount": "1",
                "newsCount": "0",
                "enableFuzzyQuery": "false",
                "quotesQueryId": "tss_match_phrase_query",
                "multiQuoteQueryId": "multi_quote_single_token_query",
                "newsQueryId": "news_cie_vespa",
                "enableCb": "true",
                "enableNavLinks": "true",
                "enableEnhancedTrivialQuery": "true"
            }, headers=self.headers)
            response.raise_for_status()
            self.search_cache[query_encoded] = response.json()
        return YahooSearchResult(self.search_cache[query_encoded])

    def _get_with_cookie_refresh(self, url, params={}):
        response = requests.get(url, cookies=self.cookies, params={**params, **{"crumb": self.crumb}},
                                headers=self.headers)
        if response.status_code in [401, 403]:
            self._get_cookies_and_crumb()
            response = requests.get(url, cookies=self.cookies, params={**params, **{"crumb": self.crumb}},
                                    headers=self.headers)
        return response

    # copy paste from https://github.com/ranaroussi/yfinance/blob/main/yfinance/data.py but without configuration bloat
    def _get_cookies_and_crumb(self):

        self.cookies = {}
        self.crumb = None

        base_args = {
            'headers': self.headers
        }

        get_args = {**base_args, 'url': 'https://guce.yahoo.com/consent'}
        with requests.Session() as s:
            response = s.get(**get_args)
            soup = BeautifulSoup(response.content, 'html.parser')
            csrfTokenInput = soup.find('input', attrs={'name': 'csrfToken'})
            csrfToken = csrfTokenInput['value']
            sessionIdInput = soup.find('input', attrs={'name': 'sessionId'})
            sessionId = sessionIdInput['value']

            originalDoneUrl = 'https://finance.yahoo.com/'
            namespace = 'yahoo'
            data = {
                'agree': ['agree', 'agree'],
                'consentUUID': 'default',
                'sessionId': sessionId,
                'csrfToken': csrfToken,
                'originalDoneUrl': originalDoneUrl,
                'namespace': namespace,
            }
            post_args = {**base_args,
                'url': f'https://consent.yahoo.com/v2/collectConsent?sessionId={sessionId}',
                'data': data}
            get_args = {**base_args,
                'url': f'https://guce.yahoo.com/copyConsent?sessionId={sessionId}',
                'data': data}
            s.post(**post_args)
            s.get(**get_args)
            self.cookies = s.cookies

            get_args = {
                'url': 'https://query2.finance.yahoo.com/v1/test/getcrumb',
                'headers': self.headers,
            }
            r = s.get(**get_args)
            self.crumb = r.text
