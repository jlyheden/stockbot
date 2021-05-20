import logging
import requests
import re

from datetime import datetime, time
from lxml.html.soupparser import fromstring

from stockbot.provider.base import BaseQuoteService, BaseQuote

LOGGER = logging.getLogger(__name__)


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


class AvanzaFundQuote(BaseQuote):

    def __init__(self, *args, **kwargs):
        self.data = kwargs.get("data", dict())
        for k, v in self.data.items():
            setattr(self, k, v)
        self.fields = [
            ["Name", self.name],
            ["%1D", self.developmentOneDay],
            ["%1M", self.developmentOneMonth],
            ["%1Y", self.developmentOneYear],
            ["%YTD", self.developmentThisYear],
            ["Fee", "{}%".format(self.productFee)]
        ]
        if self.rating:
            self.fields.append(["Rating", "{}/5".format(self.rating)])
        try:
            self.fields.append(
              ["Top 3 Holdings", "|".join([
                "{c}:{l}:{w}%".format(
                    c=self.holdingChartData[i].get("name"),
                    l=self.holdingChartData[i].get("countryCode"),
                    w=self.holdingChartData[i].get("y")
                ) for i in range(3)])
               ]
            )
        except Exception as e:
            LOGGER.exception("Failed to parse holdings data")


class AvanzaQuote(BaseQuote):

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
                    self.recommendationString = "{b}/{h}/{s}".format(
                        b=self.buyRecommendation, h=self.holdRecommendation, s=self.sellRecommendation)
                else:
                    self.recommendationString = ""

        self.fields = [
            ["Name", self.name],
            ["Price", self.lastPrice],
            ["Low Price", self.lowestPrice],
            ["High Price", self.highestPrice],
            ["%1D", self.percentChange],
            ["%YTD", self.totalReturnYtd]
        ]

        if len(self.recommendationString) > 0:
            self.fields.append(["Recommendations (B/H/S)", self.recommendationString])

        self.fields.append(["Update Time", self.lastUpdateTime])

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
                    return self.__quote_factory(search_result_entry.get('link'))
                except Exception as e:
                    LOGGER.exception("Failed to retrieve quote for {}".format(ticker))
                    return AvanzaFallbackQuote(quote_type="error")
        return AvanzaFallbackQuote(quote_type="didn't find any quote for {}".format(ticker))

    def __quote_factory(self, link):
        if "/fonder/om-fonden.html/" in link:
            return self.__get_fund_quote(link)
        response = requests.get(link)
        response.raise_for_status()
        tree = fromstring(response.text)
        quote_type_element = tree.xpath("//div[@id='surface']")
        if len(quote_type_element) > 0:
            quote_type = quote_type_element[0].attrib['data-page_type']
            if quote_type in ('stock', 'index', 'etf', 'certificate'):
                return AvanzaQuote(tree=tree)
            else:
                LOGGER.warning("Unknown quote type: {}".format(quote_type))
                return AvanzaFallbackQuote(quote_type=quote_type)
        else:
            LOGGER.warning("Cannot determine quote type")
            return AvanzaFallbackQuote(quote_type="no such element")

    def __get_fund_quote(self, link):
        id_ = link.split("/")[5]
        response = requests.get("https://www.avanza.se/_api/fund-guide/guide/{id_}".format(id_=id_))
        response.raise_for_status()
        data = response.json()
        return AvanzaFundQuote(data=data)

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
