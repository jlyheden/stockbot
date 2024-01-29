import json
import os
import unittest

from datetime import datetime
from unittest.mock import patch

import vcr

from stockbot.persistence import DatabaseCollection, ScheduledCommand
from stockbot.provider import Analytics, QuoteServiceFactory
from stockbot.provider.bloomberg import BloombergQuote, BloombergQueryService, BloombergSearchResult
from stockbot.provider.google import GoogleFinanceQueryService, GoogleFinanceQuote, GoogleFinanceSearchResult,\
    StockDomain
from stockbot.provider.nasdaq import NasdaqIndexScraper
from stockbot.provider.avanza import AvanzaQuote, AvanzaQueryService, AvanzaSearchResult
from stockbot.provider.ig import IGQueryService
from stockbot.provider.ibindex import IbIndexQueryService
from stockbot.provider.yahoo import YahooQueryService

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
        self.assertEquals("Name: OMX Stockholm 30 Index, Price: 1642.49, Open Price: 1647.925, Low Price: 1642.214, High Price: 1651.131, Percent Change 1 Day: -0.329748, Total Return YTD: 8.25818928, Update Time: {}".format(d_string), str(tm))

    def test_parse_nodata(self):
        """instantiate without valid quotedata"""
        tm = BloombergQuote()
        self.assertEquals("N/A", tm.name)
        self.assertEquals("Name: N/A, Price: N/A, Open Price: N/A, Low Price: N/A, High Price: N/A, Percent Change 1 Day: N/A, Total Return YTD: N/A, Update Time: N/A", str(tm))

    def test_is_empty(self):

        quote = BloombergQuote()
        self.assertTrue(quote.is_empty())

        quote = BloombergQuote(message={"basicQuote": {"name": "foobar"}})
        self.assertFalse(quote.is_empty())

    @patch('stockbot.provider.bloomberg.datetime')
    def test_is_fresh(self, datetime_mock):

        # timestamp of when the quote was last updated
        timestamp = 1507645468

        # compare with now() 15 minutes into the future
        datetime_mock.now.return_value = datetime.fromtimestamp(timestamp + (15*60))
        datetime_mock.fromtimestamp.side_effect = lambda *args, **kw: datetime.fromtimestamp(*args, **kw)
        datetime_mock.side_effect = lambda *args, **kw: datetime(*args, **kw)
        tm = BloombergQuote(message={
            "basicQuote": {
                "name": "foobar",
                "lastUpdateEpoch": str(timestamp)
            }
        })
        self.assertTrue(tm.is_fresh())

        # compare with now() 16 minutes into the future
        datetime_mock.now.return_value = datetime.fromtimestamp(timestamp + (17*60))
        self.assertFalse(tm.is_fresh())

        # compare with now() 1 day into the future
        datetime_mock.now.return_value = datetime.fromtimestamp(timestamp + 86400)
        self.assertFalse(tm.is_fresh())

        # if lastUpdateEpoch is missing for some reason should not crash the application
        tm = BloombergQuote(message={
            "basicQuote": {
                "name": "foobar"
            }
        })
        datetime_mock.now.return_value = datetime.fromtimestamp(timestamp + (15*60))
        self.assertFalse(tm.is_fresh())


class TestBloombergQueryService(unittest.TestCase):

    def setUp(self):
        self.service = BloombergQueryService()

    @vcr.use_cassette('mock/vcr_cassettes/bloomberg/search/dax.yaml')
    def test_search_result_incomplete_results(self):
        res = self.service.search("dax")
        self.assertEquals(BloombergSearchResult, type(res))
        self.assertIn("Ticker: DAX:IND, Country: DE, Name: Deutsche Boerse AG German Stock Index DAX, Type: Index", res.result_as_list())


class TestIGQueryService(unittest.TestCase):

    def setUp(self):
        self.service = IGQueryService()

    @vcr.use_cassette('mock/vcr_cassettes/ig/quote/sweden-30.yaml')
    def test_get_quote(self):
        res = self.service.get_quote("sweden-30")
        self.assertEqual(res.name, "Sweden 30")
        self.assertEqual(res.ticker, "OMXS30")
        self.assertEqual(float, type(res.sell_price))
        self.assertEqual(float, type(res.buy_price))
        self.assertEqual(float, type(res.price_change_points))
        self.assertEqual(float, type(res.price_change_percent))
        self.assertRegexpMatches(str(res), "^Name: OMXS30, Buy Price: [0-9]+\.[0-9]+, Sell Price: [0-9]+\.[0-9]+, Percent Change: [0-9]+\.[0-9]+, Points Change: [0-9]+\.[0-9]+$")


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
        for field in StockDomain.__table__.columns.keys():
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


class TestAvanzaQueryService(unittest.TestCase):

    def setUp(self):
        self.service = AvanzaQueryService()

    @vcr.use_cassette('mock/vcr_cassettes/avanza/search/dax.yaml')
    def test_search(self):
        ticker = "dax"
        result = self.service.search(ticker)
        self.assertEqual(type(result), AvanzaSearchResult)
        self.assertTrue(len(result.result) > 0)
        self.assertEqual(result.result[0]["name"], "DAX")

    @vcr.use_cassette('mock/vcr_cassettes/avanza/quote/avanza.yaml')
    def test_get_quote(self):
        ticker = "avanza"
        quote = self.service.get_quote(ticker)
        self.assertEqual(type(quote), AvanzaQuote)
        self.assertEqual("Name: Avanza Bank Holding, Price: 389.0, Low Price: 385.0, High Price: 389.6, %1D: 0.41, %YTD: 13.05, Recommendations (B/H/S): 1/2/1, Update Time: 11:15:48", str(quote))

    @vcr.use_cassette('mock/vcr_cassettes/avanza/quote/dax.yaml')
    def test_get_index(self):
        ticker = "dax"
        quote = self.service.get_quote(ticker)
        self.assertEqual(type(quote), AvanzaQuote)
        self.assertEqual(quote.lastPrice, 12540.73)
        self.assertEqual(quote.lowestPrice, 12499.30)
        self.assertEqual(quote.highestPrice, 12583.79)

    @vcr.use_cassette('mock/vcr_cassettes/avanza/quote/avanza_zero.yaml')
    def test_get_fund(self):
        ticker = "avanza zero"
        quote = self.service.get_quote(ticker)
        self.assertEqual(str(quote), "Name: Avanza Zero, %1D: 1.75663, %1M: 2.08861, %1Y: 47.45233, %YTD: 21.5053, Fee: 0.0%, Rating: 3/5, Top 3 Holdings: Atlas Copco A:SE:7.91%|Ericsson B:SE:6.55%|Evolution:SE:6.5%")

    @vcr.use_cassette('mock/vcr_cassettes/avanza/quote/xact_ravaror.yaml')
    def test_get_etf_quote(self):
        ticker = "xact ravaror"
        quote = self.service.get_quote(ticker)
        self.assertEqual(type(quote), AvanzaQuote)
        self.assertEqual(quote.lastPrice, 161.0)
        self.assertEqual(quote.lowestPrice, 160.9)
        self.assertEqual(quote.highestPrice, 162.1)


class TestIbIndexQueryService(unittest.TestCase):

    def setUp(self):
        self.service = IbIndexQueryService()

    @vcr.use_cassette('mock/vcr_cassettes/ibindex/quote/all.yaml')
    def test_search_for_existing_quote(self):
        text = "investor"
        result = self.service.search(text)
        self.assertEquals("Result: Ticker: INVE B", str(result))

    @vcr.use_cassette('mock/vcr_cassettes/ibindex/quote/all.yaml')
    def test_search_for_non_existing_quote(self):
        text = "abcdefghijlkmnop"
        result = self.service.search(text)
        self.assertEquals("Result: Nada", str(result))

    @vcr.use_cassette('mock/vcr_cassettes/ibindex/quote/all.yaml')
    def test_search_with_multiple_matches(self):
        text = "invest"
        result = self.service.search(text)
        self.assertEquals("Result: Ticker: HAV B | Ticker: INVE B", str(result))

    @vcr.use_cassette('mock/vcr_cassettes/ibindex/quote/all.yaml')
    def test_search_with_multiple_matches_ranked_result(self):
        text = "invest"
        result = self.service.search(text)
        result.get_ranked_ticker()
        self.assertEquals("INVE B", result.get_ranked_ticker())

    @vcr.use_cassette('mock/vcr_cassettes/ibindex/quote/all.yaml')
    def test_query_existing_quote(self):
        text = "inve b"
        result = self.service.get_quote(text)
        self.assertEquals("Name: Investor B, NAV rebate percentage (reported): 15.455, NAV rebate percentage ("
                          "calculated): 21.330, NAV datechange: 2020-04-22 00:00:00", str(result))

    @vcr.use_cassette('mock/vcr_cassettes/ibindex/quote/all.yaml')
    def test_query_nonexisting_quote(self):
        text = "abcdefghijklmnop"
        result = self.service.get_quote(text)
        self.assertEquals("No such quote: abcdefghijklmnop", str(result))


class TestYahooQueryService(unittest.TestCase):

    def setUp(self):
        self.service = YahooQueryService()

    @vcr.use_cassette('mock/vcr_cassettes/yahoo/quote/omx_stockholm.yaml')
    def test_get_existing_index(self):
        text = "stockholm"
        result = self.service.get_quote(text)
        self.assertRegexpMatches(str(result), "^Name: OMX Stockholm 30 Index, Price: [0-9\.]+, Low Price: [0-9\.]+, High Price: [0-9\.]+, Percent Change 1 Day: [0-9\.\-]+, Market: se_market, Chart: https://finance.yahoo.com/chart/%5EOMX, Update Time: [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}")

    @vcr.use_cassette('mock/vcr_cassettes/yahoo/quote/none_found.yaml')
    def test_get_no_such_instrument(self):
        text = "foo bar baz"
        result = self.service.get_quote(text)
        self.assertEquals("Didn't find anything", str(result))

    @vcr.use_cassette('mock/vcr_cassettes/yahoo/quote/microsoft.yaml')
    def test_get_existing_company(self):
        text = "microsoft"
        result = self.service.get_quote(text)
        self.assertRegexpMatches(str(result), "^Name: Microsoft Corporation, Price: [0-9\.]+, Low Price: [0-9\.]+, High Price: [0-9\.]+, Percent Change 1 Day: [0-9\.\-]+, Market: us_market, Chart: https://finance.yahoo.com/chart/MSFT, Update Time: [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}")

    @vcr.use_cassette('mock/vcr_cassettes/yahoo/quote/bytedance.yaml')
    def test_get_existing_company(self):
        text = "bytedance"
        result = self.service.get_quote(text)
        self.assertEqual("Didn't find anything", str(result))
