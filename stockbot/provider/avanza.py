import logging
import requests
import re

from datetime import datetime, time
from lxml.html.soupparser import fromstring

from stockbot.provider.base import BaseQuoteService

LOGGER = logging.getLogger(__name__)


class AvanzaQuote(object):

    def __init__(self, *args, **kwargs):
        data = kwargs.get('message', None)

        if data is not None:
            tree = fromstring(data)
            quote_root = tree.xpath("//div[contains(@class,'quote')]//ul[contains(@class,'quoteBar')]")[0]
            self.currency = quote_root.attrib['data-currency'].rstrip().lstrip()
            try:
                self.name = quote_root.attrib['data-intrument_name']
            except:
                # bla
                div = tree.xpath("//div[contains(@class,'controlPanel')]/div[contains(@class,'displayName')]")
                self.name = div[0].text.lstrip().rstrip()
            try:
                self.percentChange = float(quote_root.attrib['data-change_percent'])
            except:
                # bla
                span = tree.xpath("//span[contains(@class,'changePercent')]")
                raw_percentage = span[0].text
                stripped_percentage = re.sub('[^0-9\-,]*', '', raw_percentage)
                self.percentChange = float(re.sub(',', '.', stripped_percentage))

            try:
                self.ticker = quote_root.attrib['data-short_name']
            except:
                self.ticker = self.name

            for price_element in quote_root.xpath("//span[contains(@class,'Price')]"):
                # some prices have additional markup so have to use text_content() to merge all children if there are any
                # https://lxml.de/lxmlhtml.html#html-element-methods
                if price_element.text_content() is not None:
                    attr_name = [x for x in price_element.attrib['class'].split(" ") if x.endswith("Price")][0]
                    stripped_value = re.sub('[^0-9,]*', '', price_element.text_content())
                    setattr(self, attr_name, float(re.sub(',', '.', stripped_value)))

            # get date
            try:
                date_element = quote_root.xpath("//span[contains(@class,'updated')]")[0]
                self.lastUpdateTime = date_element.text
            except:
                LOGGER.exception("Failed to retrieve time")

    def __str__(self):
        return "Name: {n}, Price: {op}, Low Price: {lp}, High Price: {hp}, Percent Change 1 Day: {p1d}, Update Time: {ut}" \
            .format(n=self.name, op=self.lastPrice, lp=self.lowestPrice, hp=self.highestPrice,
                    p1d=self.percentChange, ut=self.lastUpdateTime)

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


class AvanzaSearchResult(object):

    def __init__(self, *args, **kwargs):
        self.result = []
        html_response = kwargs.get('message')

        tree = fromstring(html_response)
        responses = tree.xpath("//ul[contains(@class,'globalSrchRes')]//a[contains(@class,'srchResLink')]")
        for response in responses:
            self.result.append(dict(
                name=response.attrib['title'],
                link="https://www.avanza.se{path}".format(path=response.attrib['href']),
                ctype=response.attrib['data-ctype']
            ))

    def __str__(self):
        return "Result: {r}".format(r=" | ".join(
            ["Name: {n}, Link: {c}, Type: {t}".format(n=x.get("name", None),
                                                      c=x.get("link", None),
                                                      t=x.get("ctype", None))
             for x in self.result
             ]
        ))

    def result_as_list(self):
        return ["Name: {n}, Link: {c}, Type: {t}".format(n=x.get("name", None),
                                                         c=x.get("link", None),
                                                         t=x.get("ctype", None))
                for x in self.result
                ]

    def get_tickers(self):
        return [x.get("link", None) for x in self.result]

    def is_empty(self):
        return len(self.result) == 0


class AvanzaQueryService(BaseQuoteService):
    # search results probably don't change that much so cache them
    search_cache = {}

    def __init__(self, *args, **kwargs):
        pass

    def get_quote(self, ticker):
        search_result = self.search(ticker)
        try:
            response = requests.get(search_result.result[0]['link'])
            return AvanzaQuote(message=self.__sanitize_avanza_response(response.text))
        except IndexError:
            return AvanzaQuote()

    def search(self, query):
        if query not in self.search_cache:
            LOGGER.info("Response from query {q} not in cache, will query avanzas search".format(q=query))
            try:
                response = requests.get(self.__search_url(query))
                self.search_cache[query] = AvanzaSearchResult(message=self.__sanitize_avanza_response(response.text))
            except Exception as e:
                return None
        return self.search_cache[query]

    @staticmethod
    def __search_url(query):
        url = "https://www.avanza.se/ab/sok/inline?query={query}".format(query=query)
        LOGGER.debug("search url: {}".format(url))
        return url

    @staticmethod
    def __sanitize_avanza_response(response):
        # remove carriage return
        modified = re.sub('\r', '', response, flags=re.MULTILINE)
        return modified
