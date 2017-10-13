import json
import requests
import logging
import re

from urllib.parse import urlencode

LOGGER = logging.getLogger(__name__)


class GoogleFinanceQuote(object):

    def __init__(self, *args, **kwargs):
        pattern = re.compile("^[0-9,.]+$")
        data = kwargs.get('message', {})
        for k, v in data.items():
            # remove + from price change if positive
            if k == 'c' or k == 'cp':
                v = v.lstrip("+")
            # remove comma from values
            if isinstance(v, str) and pattern.match(v):
                v = v.replace(",", "")
            setattr(self, k, v)

    def __str__(self):
        return "Name: {n}, Price: {p}, Open Price: {op}, Low Price: {lp}, High Price: {hp}, Percent Change: {p1d}"\
            .format(n=self.name, p=self.l, op=self.op, lp=self.lo, hp=self.hi, p1d=self.cp)

    def __getattribute__(self, item):
        try:
            # we cannot use this objects getattribute because then we loop until the world collapses
            return object.__getattribute__(self, item)
        except Exception as e:
            LOGGER.exception("Failed to look up attribute {}".format(item))
            return "N/A"


class GoogleFinanceSearchResult(object):

    def __init__(self, *args, **kwargs):
        self.result = kwargs.get('result')["matches"]

    def __str__(self):
        return "Result: {r}".format(r=" | ".join(
            ["Ticker: {t}, Market: {m}, Name: {n}".format(t=x["t"], m=x["e"], n=x["n"]) for x in self.result]
        ))

    def result_as_list(self):
        return ["Ticker: {t}, Market: {m}, Name: {n}".format(t=x["t"], m=x["e"], n=x["n"]) for x in self.result]

    def is_empty(self):
        return len(self.result) == 0


class GoogleFinanceQueryService(object):

    # search results probably don't change that much so cache them
    search_cache = {}

    def get_quote(self, ticker):
        url = self.__quote_url(ticker)
        req = requests.get(url)
        if req.ok:
            j = json.loads(req.content[6:-2].decode('unicode_escape'))
            return GoogleFinanceQuote(message=j)

    def search(self, query):
        if query not in self.search_cache:
            LOGGER.info("Response from query {q} not in cache, will query google finance search api".format(q=query))
            try:
                self.search_cache[query] = self.__search_query(query)
            except Exception as e:
                return None
        return self.search_cache[query]

    def __search_query(self, query):
        url = self.__search_url(query)
        try:
            req = requests.get(url)
            if req.ok:
                j = json.loads(req.text)
                return GoogleFinanceSearchResult(result=j)
            else:
                raise Exception("Failed to query google finance search api. Code: {c}, Text: {t}".format(
                    c=req.status_code, t=req.text))
        except Exception as e:
            LOGGER.exception("Failed to search for {q}, search url: {u}".format(q=query, u=url))
            raise

    def __quote_url(self, ticker):
        params = {
            "q": ticker,
            "output": "json"
        }
        url = "https://finance.google.com/finance?{params}".format(params=urlencode(params))
        LOGGER.debug("quote_url: {}".format(url))
        return url

    def __search_url(self, query):
        params = {
            "matchtype": "matchall",
            "q": query
        }
        url = "https://finance.google.com/finance/match?{params}".format(params=urlencode(params))
        LOGGER.debug("search_url: {}".format(url))
        return url
