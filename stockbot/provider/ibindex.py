import requests
import datetime
from functools import lru_cache

from stockbot.provider.base import BaseQuoteService


class IbIndexNonExistingQuote(object):

    def __init__(self, ticker):
        self.name = ticker

    def __str__(self):
        return "No such quote: {name}".format(name=self.name)


class IbIndexQuote(object):

    def __init__(self, message):
        self.message = message
        self.name = message["productName"]
        self.nav_rebate_reported = "{:.3f}".format(message["netAssetValueRebatePremium"])
        self.nav_rebate_calculated = "{:.3f}".format(message["netAssetValueCalculatedRebatePremium"])
        self.nav_datechange = datetime.datetime.utcfromtimestamp(self.message["netAssetValueChangeDate"] / 1000)

    def __str__(self):
        return "Name: {name}, NAV rebate percentage (reported): {nav_rebate_reported}, NAV rebate percentage " \
               "(calculated): {nav_rebate_calculated}, NAV datechange: {nav_datechange}".format(
                name=self.name,
                nav_rebate_reported=self.nav_rebate_reported,
                nav_rebate_calculated=self.nav_rebate_calculated,
                nav_datechange=self.nav_datechange
                )


class IbIndexSearchResult(object):

    def __init__(self, result=None, query=None):
        self.result = result
        self.query = query

    def __str__(self):
        return "Result: {r}".format(r=" | ".join(self.result_as_list()))

    def result_as_list(self):
        result = ["Ticker: {t}".format(t=x.get("product", None)) for x in self.result]
        if len(result) == 0:
            result.append("Nada")
        return result

    def get_ranked_ticker(self):
        ranked = []
        for item in self.result:
            if self.query == item["product"].lower():
                rank = 1.0
            else:
                rank = len(self.query) / len(item["productName"])
            ranked.append((rank, item["product"]))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return ranked[0][1]


class IbIndexQueryService(BaseQuoteService):

    def __init__(self, *args, **kwargs):
        self.url = "http://ibindex.se/ibi//index/getProducts.req"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/81.0.4044.129 Safari/537.36"
        }

    def get_quote(self, ticker):
        response = requests.post(self.url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        try:
            message = [x for x in data if x["product"].lower() == ticker.lower()][0]
            return IbIndexQuote(message=message)
        except IndexError:
            return IbIndexNonExistingQuote(ticker=ticker)

    @lru_cache(maxsize=10)
    def search(self, query):
        query_lower = query.lower()
        response = requests.post(self.url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        matches = []
        for item in data:
            if query_lower == item["product"].lower() or query_lower in item["productName"].lower():
                matches.append(item)
        return IbIndexSearchResult(result=matches, query=query_lower)
