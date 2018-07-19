import logging
import requests
import re

from datetime import datetime, time
from lxml.html.soupparser import fromstring

from stockbot.provider.base import BaseQuoteService

LOGGER = logging.getLogger(__name__)


def avanza_quote_factory(html_data):
    tree = fromstring(html_data)

    quote_type_element = tree.xpath("//div[@id='surface']")
    if len(quote_type_element) > 0:
        quote_type = quote_type_element[0].attrib['data-page_type']
        if quote_type in ('stock', 'index', 'etf', 'certificate'):
            return AvanzaQuote(tree=tree)
        elif quote_type == 'fund':
            return AvanzaFundQuote(tree=tree)
        else:
            LOGGER.warning("Unknown quote type: {}".format(quote_type))
            return AvanzaFallbackQuote(quote_type=quote_type)
    else:
        LOGGER.warning("Cannot determine quote type")
        return AvanzaFallbackQuote(quote_type="no such element")


def percent_str_to_float(s):
    try:
        s1 = re.sub('[^0-9\-,]', '', s)
        return float(re.sub(',', '.', s1))
    except Exception as e:
        LOGGER.exception("Failed to cast {} to float, returning the orig value".format(s))
        return s


class AvanzaFallbackQuote(object):

    def __init__(self, *args, **kwargs):
        self.quote_type = kwargs.get('quote_type', None)

    def __str__(self):
        return "Unknown type, got: {}".format(self.quote_type)

    def is_empty(self):
        return False

    def is_fresh(self):
        return False


class AvanzaFundQuote(object):

    def __init__(self, *args, **kwargs):
        tree = kwargs.get('tree', None)

        if tree is not None:
            quote_root = tree.xpath("//div[contains(@class,'quote')]//ul[contains(@class,'quoteBar')]")[0]
            for element in quote_root.xpath("//meta[@itemprop]"):
                name = element.attrib['itemprop']
                value = element.attrib['content']
                if getattr(self, name) == "N/A":
                    if name == 'price':
                        self.price = float(value)
                    elif name == 'name' and value == 'Morningstar':
                        continue
                    else:
                        setattr(self, name, value)

            self.lastUpdateTime = quote_root.xpath("//span[@itemprop='datePublished']")[0].text.lstrip().rstrip()

            # we are lazy and depend on order here
            price_changes = quote_root.xpath("//span[contains(@class,'changePercent')]")
            self.price_change_1d = percent_str_to_float(price_changes[0].text)
            self.price_change_3m = percent_str_to_float(price_changes[1].text)
            self.price_change_1y = percent_str_to_float(price_changes[2].text)

    def __str__(self):
        return "Name: {n}, NAV: {p}, Percent Change 1 Day: {c1d}, Percent Change 3 Months: {c3m}, Percent Change 1 Year: {c1y}, Rating: {rt}, Update Time: {ut}" \
            .format(n=self.name, p=self.price, c1d=self.price_change_1d, c3m=self.price_change_3m,
                    c1y=self.price_change_1y, rt="{}/{}".format(self.ratingValue,self.bestRating),
                    ut=self.lastUpdateTime)

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
        # funds are never fresh
        return False


class AvanzaQuote(object):

    def __init__(self, *args, **kwargs):
        tree = kwargs.get('tree', None)

        if tree is not None:
            quote_root = tree.xpath("//div[contains(@class,'quote')]//ul[contains(@class,'quoteBar')]")[0]
            self.currency = quote_root.attrib['data-currency'].rstrip().lstrip()
            try:
                self.name = quote_root.attrib['data-intrument_name']
            except:
                div = tree.xpath("//div[contains(@class,'controlPanel')]/div[contains(@class,'displayName')]")
                self.name = div[0].text.lstrip().rstrip()
            try:
                self.percentChange = float(quote_root.attrib['data-change_percent'])
            except:
                span = tree.xpath("//span[contains(@class,'changePercent')]")
                raw_percentage = span[0].text
                self.percentChange = percent_str_to_float(raw_percentage)

            try:
                self.ticker = quote_root.attrib['data-short_name']
            except:
                self.ticker = self.name

            for price_element in quote_root.xpath("//span[contains(@class,'Price')]"):
                # some prices have additional markup so have to use text_content() to merge all children if there are any
                # https://lxml.de/lxmlhtml.html#html-element-methods
                if price_element.text_content() is not None:
                    attr_name = [x for x in price_element.attrib['class'].split(" ") if x.endswith("Price")][0]
                    setattr(self, attr_name, percent_str_to_float(price_element.text_content()))

            # get date
            try:
                date_element = quote_root.xpath("//span[contains(@class,'updated')]")[0]
                self.lastUpdateTime = date_element.text
            except:
                LOGGER.exception("Failed to retrieve time")

            # get history
            try:
                history_rows = tree.xpath("//div[contains(@class,'history')]/div[contains(@class,'content')]/table/tbody/tr")
                for history_row in history_rows:
                    columns = history_row.xpath("./td")
                    if columns[0].text == u'i år':
                        self.totalReturnYtd = percent_str_to_float(columns[2].text)
            except:
                LOGGER.exception("Failed to retrieve history")

            # get recommendations
            try:
                attr_map = {
                    u"Köp": "buyRecommendation",
                    u"Behåll": "holdRecommendation",
                    u"Sälj": "sellRecommendation"
                }
                recommendation_elements = quote_root.xpath("//div[contains(@class,'recommendations')]/div[contains(@class,'recommendationsContent')]//span[contains(@class,'descriptionText')]")
                for recommendation_element in recommendation_elements:
                    recommendation_text = recommendation_element.text
                    recommendation_type = recommendation_text.split(" ")[0].rstrip()  # must strip because Hold recommendation has tabs
                    if recommendation_type in attr_map.keys() and recommendation_text.endswith(")"):
                        recommendation_count = int(re.sub('[^0-9]*', '', recommendation_text, flags=re.MULTILINE))
                        setattr(self, attr_map[recommendation_type], recommendation_count)
            except:
                LOGGER.exception("Failed to parse recommendations")
                self.recommendationString = ""
            else:
                if "N/A" not in (self.buyRecommendation, self.holdRecommendation, self.sellRecommendation):
                    self.recommendationString = "Recommendations (B/H/S): {b}/{h}/{s}, ".format(
                        b=self.buyRecommendation, h=self.holdRecommendation, s=self.sellRecommendation)
                else:
                    self.recommendationString = ""

    def __str__(self):
        return "Name: {n}, Price: {op}, Low Price: {lp}, High Price: {hp}, Percent Change 1 Day: {p1d}, Total Percentage Return YTD: {ytd}, {rek}Update Time: {ut}" \
            .format(n=self.name, op=self.lastPrice, lp=self.lowestPrice, hp=self.highestPrice,
                    p1d=self.percentChange, ytd=self.totalReturnYtd, rek=self.recommendationString,
                    ut=self.lastUpdateTime)

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
        html_response = kwargs.get('message', None)

        if html_response is not None:
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
        for search_result_entry in search_result.result:
            if 'link' in search_result_entry:
                try:
                    response = requests.get(search_result_entry.get('link'))
                    return avanza_quote_factory(html_data=response.text)
                except Exception as e:
                    LOGGER.exception("Failed to retrieve quote for {}".format(ticker))
                    return AvanzaFallbackQuote(quote_type="error")
        return AvanzaFallbackQuote(quote_type="didn't find any quote for {}".format(ticker))

    def search(self, query):
        if query not in self.search_cache:
            LOGGER.info("Response from query {q} not in cache, will query avanzas search".format(q=query))
            try:
                response = requests.get(self.__search_url(query))
                self.search_cache[query] = AvanzaSearchResult(message=response.text)
            except Exception as e:
                LOGGER.exception("Failed to create proper search result")
                return AvanzaSearchResult()
        return self.search_cache[query]

    @staticmethod
    def __search_url(query):
        url = "https://www.avanza.se/ab/sok/inline?query={query}".format(query=query)
        LOGGER.debug("search url: {}".format(url))
        return url
