import logging
import requests
import re

from datetime import datetime, time
from lxml.html.soupparser import fromstring

from stockbot.provider.base import BaseQuoteService

LOGGER = logging.getLogger(__name__)


def ig_quote_factory(html_data):
    tree = fromstring(html_data)
    return IGQuote(tree=tree)


def percent_str_to_float(s):
    try:
        s1 = re.sub('[^0-9\-,]', '', s)
        return float(re.sub(',', '.', s1))
    except Exception as e:
        LOGGER.exception("Failed to cast {} to float, returning the orig value".format(s))
        return s


class IGNullQuote(object):

    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('name')

    def __str__(self):
        return "Nothing found for '{name}'".format(name=self.name)


class IGQuote(object):

    def __init__(self, *args, **kwargs):
        tree = kwargs.get('tree', None)

        if tree is not None:
            self.name = tree.xpath("//div[@class='ma-box']//h1[@class='ma__title']")[0].text
            self.ticker = tree.xpath("//div[@class='ma-box']//h1[@class='ma__title--secondary']")[0].text.lstrip("(").rstrip(")")
            self.sell_price = float(tree.xpath("//a[contains(@class, 'price-ticket__button--sell')]//div[@class='price-ticket__price']")[0].text)
            self.buy_price = float(tree.xpath("//a[contains(@class, 'price-ticket__button--buy')]//div[@class='price-ticket__price']")[0].text)
            self.price_change_points = float(tree.xpath("//div[@class='price-ticket__fluctuations']//span[@data-field='CPT']")[0].text)
            self.price_change_percent = float(tree.xpath("//div[@class='price-ticket__fluctuations']//span[@data-field='CPC']")[0].text)

    def __str__(self):
        return "Name: {n}, Buy Price: {bp}, Sell Price: {sp}, Percent Change: {pc}, Points Change: {ppc}" \
            .format(n=self.ticker, bp=self.buy_price, sp=self.sell_price, pc=self.price_change_percent,
                    ppc=self.price_change_points)

    def __getattribute__(self, item):
        try:
            # we cannot use this objects getattribute because then we loop until the world collapses
            return object.__getattribute__(self, item)
        except Exception as e:
            LOGGER.exception("Failed to look up attribute {}".format(item))
            return "N/A"

    def is_empty(self):
        try:
            return self.name == "N/A"
        except Exception:
            return True

    def is_fresh(self):
        if self.lastUpdateEpoch != "N/A":
            # most tickers are lagging 15 minutes so add another minute to avoid never getting "fresh" data
            return (datetime.now() - datetime.fromtimestamp(int(self.lastUpdateEpoch))).total_seconds() < 16 * 60
        else:
            return False


class IGQueryService(BaseQuoteService):

    def __init__(self, *args, **kwargs):
        pass

    def get_quote(self, ticker):
        try:
            response = requests.get(self.__query_url(ticker))
            return ig_quote_factory(response.text)
        except Exception as e:
            LOGGER.exception("Failed to retrieve quote for {}".format(ticker))
            return IGNullQuote(name=ticker)

    def search(self, query):
        # doesnt have search
        return []

    @staticmethod
    def __query_url(index):
        url = "https://www.ig.com/en-ch/indices/markets-indices/{index}".format(index=index)
        LOGGER.debug("search url: {}".format(url))
        return url
