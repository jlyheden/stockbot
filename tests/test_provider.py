import os
import unittest
import vcr
from stockbot.persistence import DatabaseCollection, ScheduledCommand
from stockbot.provider import QuoteServiceFactory
from stockbot.provider.ibindex import IbIndexQueryService
from stockbot.provider.yahoo import YahooQueryService

CWD = os.path.dirname(os.path.realpath(__file__))


class FakeIrcBot(object):

    commands = DatabaseCollection(type=ScheduledCommand, attribute="command")
    scheduler_interval = 3600
    scheduler = False
    callback_args = None

    def callback(self, *args):
        self.callback_args = args


class TestQuoteServiceFactory(unittest.TestCase):

    def test_get_existing_provider(self):
        factory = QuoteServiceFactory()
        self.assertEquals(YahooQueryService, type(factory.get_service("yahoo")))


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

    @unittest.skip
    @vcr.use_cassette('mock/vcr_cassettes/yahoo/quote/omx_stockholm.yaml')
    def test_get_existing_index(self):
        text = "stockholm"
        result = self.service.get_quote(text)
        self.assertRegexpMatches(str(result), "^Name: OMX Stockholm 30 Index, Price: [0-9\.]+, Low Price: [0-9\.]+, High Price: [0-9\.]+, Percent Change 1 Day: [0-9\.\-]+, Market: se_market, Chart: https://finance.yahoo.com/chart/%5EOMX, Update Time: [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}")

    @unittest.skip
    @vcr.use_cassette('mock/vcr_cassettes/yahoo/quote/none_found.yaml')
    def test_get_no_such_instrument(self):
        text = "foo bar baz"
        result = self.service.get_quote(text)
        self.assertEquals("Didn't find anything", str(result))

    @unittest.skip
    @vcr.use_cassette('mock/vcr_cassettes/yahoo/quote/microsoft.yaml')
    def test_get_existing_company_1(self):
        text = "microsoft"
        result = self.service.get_quote(text)
        self.assertRegexpMatches(str(result), "^Name: Microsoft Corporation, Price: [0-9\.]+, Low Price: [0-9\.]+, High Price: [0-9\.]+, Percent Change 1 Day: [0-9\.\-]+, Market: us_market, Chart: https://finance.yahoo.com/chart/MSFT, Update Time: [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}")

    @unittest.skip
    @vcr.use_cassette('mock/vcr_cassettes/yahoo/quote/investor.yaml')
    def test_get_existing_company_2(self):
        text = "investor ab"
        result = self.service.get_quote(text)
        self.assertRegexpMatches(str(result), "^Name: Investor AB ser. B, Price: [0-9\.]+, Low Price: [0-9\.]+, High Price: [0-9\.]+, Percent Change 1 Day: [0-9\.\-]+, Market: se_market, Chart: https://finance.yahoo.com/chart/INVE-B.ST, Update Time: [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}")
