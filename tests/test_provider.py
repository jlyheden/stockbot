import json
import os
import unittest

from datetime import datetime

import vcr

from stockbot.persistence import DatabaseCollection, ScheduledCommand
from stockbot.provider import Analytics, QuoteServiceFactory
from stockbot.provider.bloomberg import BloombergQuote, BloombergQueryService, BloombergSearchResult
from stockbot.provider.google import GoogleFinanceQueryService, GoogleFinanceQuote, GoogleFinanceSearchResult,\
    StockDomain
from stockbot.provider.nasdaq import NasdaqIndexScraper

CWD = os.path.dirname(os.path.realpath(__file__))


class FakeQuoteService(object):

    def get_quote(self, ticker):
        return "Here's your fake quote for {}".format(ticker)

    def search(self, query):
        return GoogleFinanceSearchResult(result={
            "matches": [
                {"t": "FOO", "e": "Foo Market", "n": "Foo Company"}
            ]
        })


class FakeIrcBot(object):

    commands = DatabaseCollection(type=ScheduledCommand, attribute="command")
    scheduler_interval = 3600
    scheduler = False
    callback_args = None

    def callback(self, *args):
        self.callback_args = args


class TestBloombergQuote(unittest.TestCase):

    def test_parse_withdata(self):
        """parse bloomberg json quote"""
        with open(os.path.join(CWD, "mock", "omxs30.json"), 'r') as f:
            data = json.load(f)
        tm = BloombergQuote(message=data)

        self.assertEquals("OMX:IND", tm.id)
        self.assertEquals(8.25818928, tm.totalReturnYtd)
        self.assertEquals("OMX Stockholm 30 Index", tm.name)
        self.assertEquals("", tm.primaryExchange)
        self.assertEquals(1642.49, tm.price)
        self.assertEquals("SEK", tm.issuedCurrency)
        self.assertEquals(-5.434, tm.priceChange1Day)
        self.assertEquals(-0.329748, tm.percentChange1Day)
        self.assertEquals(3, tm.priceMinDecimals)
        self.assertEquals("03:00:00.000", tm.nyTradeStartTime)
        self.assertEquals("11:35:00.000", tm.nyTradeEndTime)
        self.assertEquals(-4, tm.timeZoneOffset)
        self.assertEquals("1507645468", tm.lastUpdateEpoch)
        self.assertEquals(1647.925, tm.openPrice)
        self.assertEquals(1642.214, tm.lowPrice)
        self.assertEquals(1651.131, tm.highPrice)
        self.assertEquals(78347792, tm.volume)
        self.assertEquals(1647.924, tm.previousClosingPriceOneTradingDayAgo)
        self.assertEquals(1391.806, tm.lowPrice52Week)
        self.assertEquals(1658.873, tm.highPrice52Week)
        self.assertEquals(15.89318, tm.totalReturn1Year)
        self.assertEquals("10/10/2017", tm.priceDate)
        self.assertEquals("10:24 AM", tm.priceTime)
        self.assertEquals("10:24 AM", tm.lastUpdateTime)
        self.assertEquals("2017-10-10T14:24:28.000Z", tm.lastUpdateISO)
        self.assertEquals("EDT", tm.userTimeZone)

        d_string = datetime.fromtimestamp(1507645468).strftime("%Y-%m-%d %H:%M:%S")
        self.assertEquals("Name: OMX Stockholm 30 Index, Price: 1642.49, Open Price: 1647.925, Low Price: 1642.214, High Price: 1651.131, Percent Change 1 Day: -0.329748, Update Time: {}".format(d_string), str(tm))

    def test_parse_nodata(self):
        """instantiate without valid quotedata"""
        tm = BloombergQuote()
        self.assertEquals("N/A", tm.name)
        self.assertEquals("Name: N/A, Price: N/A, Open Price: N/A, Low Price: N/A, High Price: N/A, Percent Change 1 Day: N/A, Update Time: N/A", str(tm))

    def test_is_empty(self):

        quote = BloombergQuote()
        self.assertTrue(quote.is_empty())

        quote = BloombergQuote(message={"basicQuote": {"name": "foobar"}})
        self.assertFalse(quote.is_empty())


class TestBloombergQueryService(unittest.TestCase):

    def setUp(self):
        self.service = BloombergQueryService()

    @vcr.use_cassette('mock/vcr_cassettes/bloomberg/search/dax.yaml')
    def test_search_result_incomplete_results(self):
        res = self.service.search("dax")
        self.assertEquals(BloombergSearchResult, type(res))
        self.assertIn("Ticker: DAX:IND, Country: DE, Name: Deutsche Boerse AG German Stock Index DAX, Type: Index", res.result_as_list())


class TestGoogleFinanceQuote(unittest.TestCase):

    def test_is_empty(self):

        quote = GoogleFinanceQuote()
        self.assertTrue(quote.is_empty())

        quote = GoogleFinanceQuote(message={"name": "foobar"})
        self.assertFalse(quote.is_empty())


class TestGoogleFinanceQueryService(unittest.TestCase):

    def setUp(self):
        self.service = GoogleFinanceQueryService()
        self.maxDiff = None

    @vcr.use_cassette('mock/vcr_cassettes/google/quote/aapl.yaml')
    def test_get_quote(self):
        q = self.service.get_quote('AAPL')
        self.assertEquals("Apple Inc.", q.name)
        self.assertEquals("Name: Apple Inc., Price: 157.03, Open Price: 156.73, Low Price: 156.41, High Price: 157.28, Percent Change: 0.66", str(q))

    @vcr.use_cassette('mock/vcr_cassettes/google/search/tech.yaml')
    def test_search_query(self):
        sr = self.service.search("tech")
        self.assertIn("Ticker: TRTC, Market: OTCMKTS, Name: Terra Tech Corp", sr.result_as_list())
        self.assertIn("Ticker: TECD, Market: NASDAQ, Name: Tech Data Corp", sr.result_as_list())

    @vcr.use_cassette('mock/vcr_cassettes/google/quote/aapl.yaml')
    def test_get_quote_fundamentals(self):
        q = self.service.get_quote('AAPL')
        self.assertEquals("Name: Apple Inc., P/E: 17.86, Yield: 1.60%, Beta: 1.29, Earnings Per Share: 8.79, Net profit margin: 19.20%, Operating margin: 23.71%, Return on average assets: 10.29%, Return on average equity: 26.24%, Date: Q3 (Jul '17)", q.fundamentals("recent_quarter"))
        self.assertEquals("Name: Apple Inc., P/E: 17.86, Yield: 1.60%, Beta: 1.29, Earnings Per Share: 8.79, Net profit margin: 21.19%, Operating margin: 27.84%, EBITD margin: 32.38%, Return on average assets: 14.93%, Return on average equity: 36.90%, Date: 2016", q.fundamentals("annual"))

        self.assertEquals("Name: Apple Inc., P/E: 17.86, Yield: 1.60%, Beta: 1.29, Earnings Per Share: 8.79, Error: duration not found", q.fundamentals("foobar"))


class TestStockDomain(unittest.TestCase):

    def setUp(self):
        self.service = GoogleFinanceQueryService()

    @vcr.use_cassette('mock/vcr_cassettes/google/quote/aapl.yaml')
    def test_transform_google_quote_to_stockdomain(self):

        accepted_empty_fields = ["ebitd_margin_last_q"]

        q = self.service.get_quote('AAPL')
        do = StockDomain()
        do.from_google_finance_quote(q)
        for field in StockDomain.__table__.columns._data.keys():
            value = getattr(do, field)
            if type(value) is float and field not in accepted_empty_fields:
                if value == 0.0:
                    print("Failed field: {}".format(field))
                self.assertNotEquals(0.0, value)

    def test_transform_negative_number(self):
        """ catch regression where greedy regex strips negative numbers into positive """

        quote = GoogleFinanceQuote(message={
            "name": "foo",
            "ticker": "foo",
            "pe": "-10.23",
            "keyratios": []
        })
        do = StockDomain()
        do.from_google_finance_quote(quote)
        self.assertEquals(-10.23, do.price_to_earnings)


class TestAnalytics(unittest.TestCase):

    def setUp(self):
        self.analytics = Analytics()

    def test_sort_by(self):
        collection = [
            GoogleFinanceQuote(message={
                "pe": 12,
                "beta": 44,
                "name": "Foostock1"
            }),
            GoogleFinanceQuote(message={
                "pe": 15,
                "beta": 74,
                "name": "Foostock2"
            }),
            GoogleFinanceQuote(message={
                "pe": 4,
                "beta": 74,
                "name": "Foostock3"
            }),
        ]

        # sort by one key
        result = self.analytics.sort_by(collection, attributes=["pe"])
        self.assertNotEquals(collection, result)
        self.assertEquals("Foostock3", result[0].name)
        self.assertEquals("Foostock2", result[2].name)

        # sort by two keys
        result = self.analytics.sort_by(collection, attributes=["beta", "pe"])
        self.assertNotEquals(collection, result)
        self.assertEquals("Foostock1", result[0].name)
        self.assertEquals("Foostock2", result[2].name)

        # max result 1
        result = self.analytics.sort_by(collection, attributes=["pe"], max_results=1)
        self.assertNotEquals(collection, result)
        self.assertEquals("Foostock3", result[0].name)
        self.assertEquals(1, len(result))


class TestNasdaqIndexScraper(unittest.TestCase):

    @vcr.use_cassette('mock/vcr_cassettes/nasdaq/large_cap.yaml')
    def test_scrape_large_cap(self):
        scraper = NasdaqIndexScraper()
        res = scraper.scrape("Nordic Large Cap")
        self.assertIn("Avanza Bank Holding", res)

    @vcr.use_cassette('mock/vcr_cassettes/nasdaq/mid_cap.yaml')
    def test_scrape_mid_cap(self):
        scraper = NasdaqIndexScraper()
        res = scraper.scrape("Nordic Mid Cap")
        self.assertIn("AddLife B", res)

    @vcr.use_cassette('mock/vcr_cassettes/nasdaq/small_cap.yaml')
    def test_scrape_small_cap(self):
        scraper = NasdaqIndexScraper()
        res = scraper.scrape("Nordic Small Cap")
        self.assertIn("Aspocomp Group Oyj", res)


class TestQuoteServiceFactory(unittest.TestCase):

    def test_get_existing_provider(self):

        factory = QuoteServiceFactory()

        # check that correct service is returned
        self.assertEquals(GoogleFinanceQueryService, type(factory.get_service("google")))
        self.assertEquals(BloombergQueryService, type(factory.get_service("bloomberg")))

        # check that the same instance is returned on each invocation
        self.assertEquals(factory.get_service("google"), factory.get_service("google"))
        self.assertEquals(factory.get_service("bloomberg"), factory.get_service("bloomberg"))
