import json
import os
import unittest
import threading

from datetime import datetime
from unittest.mock import patch

import vcr

from stockbot.db import create_tables, Session, drop_tables
from stockbot.persistence import DatabaseCollection, ScheduledCommand
from stockbot.provider import Analytics, root_command, QuoteServiceFactory
from stockbot.provider.bloomberg import BloombergQuote, BloombergQueryService, BloombergSearchResult
from stockbot.provider.google import GoogleFinanceQueryService, GoogleFinanceQuote, GoogleFinanceSearchResult,\
    StockDomain
from stockbot.provider.nasdaq import NasdaqIndexScraper, NasdaqCompany

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


class TestCommand(unittest.TestCase):

    def setUp(self):

        self.ircbot = FakeIrcBot()
        self.service = FakeQuoteService()
        self.session = Session()
        create_tables()

    def tearDown(self):
        drop_tables()
        self.session.close()

    def __cmd_wrap(self, *args):
        """ test helper """
        factory = QuoteServiceFactory()
        factory.providers = {"fakeprovider": FakeQuoteService}
        return root_command.execute(*args, command_args={"service_factory": factory, "instance": self.ircbot})

    def test_quote_get_command(self):

        command = ["quote", "get", "fakeprovider", "aapl"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Here's your fake quote for aapl", res)

    def test_lucky_quote_and_quick_get_command(self):

        class FakeQuote(object):

            def __init__(self, data={}):
                self.data = data

            def is_empty(self):
                return len(self.data.items()) == 0

            def __str__(self):
                return "Ticker: {}".format(self.data.get("ticker"))

        class FakeQuoteServiceLocal(object):

            def get_quote(self, ticker):
                if ticker == "fancyticker":
                    return FakeQuote()
                else:
                    return FakeQuote(data={"ticker": "AWESOMO"})

            def search(self, query):
                return GoogleFinanceSearchResult(result={
                    "matches": [
                        {"t": "AWESOMO", "e": "Foo Market", "n": "Foo Company"}
                    ]
                })

        factory = QuoteServiceFactory()
        factory.providers = {"fakeprovider": FakeQuoteServiceLocal}
        command = ["q", "gl", "fakeprovider", "fancyticker"]
        res = root_command.execute(*command, command_args={"service_factory": factory, "instance": self.ircbot})
        self.assertEquals("Ticker: AWESOMO", str(res))

        factory.providers = {"bloomberg": FakeQuoteServiceLocal}
        command = ["qq", "fancyticker"]
        res = root_command.execute(*command, command_args={"service_factory": factory, "instance": self.ircbot})
        self.assertEquals("Ticker: AWESOMO", str(res))

    def test_quote_get_command_invalid_input(self):

        command = ["quote", "get", "aapl"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("No such provider 'aapl'", res)

        command = ["quote", "get", "invalid-provider", "aapl"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("No such provider 'invalid-provider'", res)

    def test_quote_search_command(self):

        command = ["quote", "search", "fakeprovider", "foobar"]
        res = self.__cmd_wrap(*command)
        self.assertIn("Ticker: FOO, Market: Foo Market, Name: Foo Company", res)

    def test_quote_search_command_invalid_input(self):

        command = ["quote", "search", "foobar"]
        res = self.__cmd_wrap(*command)
        self.assertIn("No such provider 'foobar", res)

        command = ["quote", "search", "invalid-provider", "foobar"]
        res = self.__cmd_wrap(*command)
        self.assertIn("No such provider 'invalid-provider", res)

    def test_execute_help_command(self):

        command = ["help"]
        res = self.__cmd_wrap(*command)
        self.assertIn("quote(q) get <provider> <ticker>", res)
        self.assertIn("quote(q) search <provider> <ticker>", res)

    def test_execute_scheduler_ticker_commands(self):

        # blank state
        command = ["quote", "scheduler", "command", "get"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("No commands added", res)

        # add command
        command = ["quote", "scheduler", "command", "add", "quote", "get", "google", "foobar"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Added command: quote get google foobar", res)

        # add command again and fail gracefully
        command = ["quote", "scheduler", "command", "add", "quote", "get", "google", "foobar"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Command already in list", res)

        # verify command is there
        command = ["quote", "scheduler", "command", "get"]
        res = self.__cmd_wrap(*command)
        self.assertIn("Command: quote get google foobar", res)

        # remove command
        command = ["quote", "scheduler", "command", "remove", "quote", "get", "google", "foobar"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Removed command: quote get google foobar", res)

        # verify command is not there
        command = ["quote", "scheduler", "command", "get"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("No commands added", res)

        # remove it again and fail gracefully
        command = ["quote", "scheduler", "command", "remove", "quote", "get", "google", "foobar"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Command not in list", res)

    def test_execute_scheduler_interval_command(self):

        # default state
        command = ["quote", "scheduler", "interval", "get"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Interval: 3600 seconds", res)

        # update interval
        command = ["quote", "scheduler", "interval", "set", "60"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("New interval: 60 seconds", res)

        # get updated state
        command = ["quote", "scheduler", "interval", "get"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Interval: 60 seconds", res)

        # set garbage input
        command = ["quote", "scheduler", "interval", "set", "horseshit"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Can't set interval from garbage input, must be of an int", res)

    def test_execute_scheduler_toggle_command(self):

        command = ["quote", "scheduler", "enable"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Scheduler: enabled", res)
        self.assertTrue(self.ircbot.scheduler)

        command = ["quote", "scheduler", "disable"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Scheduler: disabled", res)
        self.assertFalse(self.ircbot.scheduler)

    def test_execute_unknown_command(self):

        command = ["hi", "stockbot"]
        res = self.__cmd_wrap(*command)
        self.assertEquals(None, res)

    @vcr.use_cassette('mock/vcr_cassettes/nasdaq/scraper.yaml')
    def test_execute_scrape_nasdaq(self):

        command = ["scrape", "nasdaq"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Scraped 657 companies from Nasdaq", res)

        command = ["scrape", "stats"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Scraped: nordic large cap=201, nordic mid cap=219, nordic small cap=237", res)

    @patch('time.sleep')
    @vcr.use_cassette('mock/vcr_cassettes/google/quote/scrape_large_cap.yaml')
    def test_execute_nonblocking_scrape_stocks(self, sleep_mock):

        # Mock sleep in the scrape task
        sleep_mock.return_value = False

        companies = [
            NasdaqCompany(name="AAK", ticker="AAK", currency="SEK", category="bla", segment="nordic large cap"),
            NasdaqCompany(name="ABB Ltd", ticker="ABB", currency="SEK", category="bla", segment="nordic large cap")
        ]
        self.session.add_all(companies)
        self.session.commit()

        command = ["scrape", "stocks", "sek", "nordic", "large", "cap"]
        root_command.execute(*command, command_args={'service': GoogleFinanceQueryService()},
                             callback=self.ircbot.callback)

        self.assertEquals("Task started", self.ircbot.callback_args[0])

        for t in threading.enumerate():
            if t.name == "thread-sek_nordic_large_cap":
                t.join()

        self.assertEquals("Done scraping segment 'nordic large cap' currency 'SEK' - scraped 2 companies",
                          self.ircbot.callback_args[0])

        for c in companies:
            row = self.session.query(StockDomain).filter(StockDomain.ticker == c.ticker).first()
            self.assertNotEquals(None, row)

    def test_execute_analytics_fields(self):

        command = ["fundamental", "fields"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Fields: id, name, ticker, net_profit_margin_last_q, net_profit_margin_last_y, operating_margin_last_q, operating_margin_last_y, ebitd_margin_last_q, ebitd_margin_last_y, roaa_last_q, roaa_last_y, roae_last_q, roae_last_y, market_cap, price_to_earnings, beta, earnings_per_share, dividend_yield, latest_dividend", res)

    def test_execute_analytics_top(self):
        # TODO: fix test data

        command = ["fundamental", "top", "5", "net_profit_margin_last_q"]
        res = self.__cmd_wrap(*command)
        self.assertEquals(["Nothing found"], res)

        command = ["fundamental", "top", "foobar", "net_profit_margin_last_q"]
        res = self.__cmd_wrap(*command)
        self.assertEquals(["Error: foobar is not a number sherlock"], res)

        command = ["fundamental", "top", "5", "this_field_doesnt_exist"]
        res = self.__cmd_wrap(*command)
        self.assertEquals(["Error: 'this_field_doesnt_exist' is not a valid field"], res)


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
