import threading
import unittest
import vcr

from unittest.mock import patch

from stockbot.command import root_command
from stockbot.db import Session, create_tables, drop_tables
from stockbot.persistence import DatabaseCollection, ScheduledCommand
from stockbot.provider import QuoteServiceFactory


class FakeQuoteServiceSearchResult(object):

    def __init__(self, result):
        self.result = result

    def result_as_list(self):
        return ["Ticker: {}, Market: {}, Name: {}".format(n["t"], n["e"], n["n"]) for n in self.result["matches"]]


class FakeQuoteService(object):

    def get_quote(self, ticker):
        return "Here's your fake quote for {}".format(ticker)

    def search(self, query):
        if query == 'none-type-response':
            return None
        return FakeQuoteServiceSearchResult(result={
            "matches": [
                {"t": "FOO", "e": "Foo Market", "n": "Foo Company"}
            ]
        })


class FakeChatService(object):

    def say(self, msg):
        return "hello friend"


class FakeIrcBot(object):

    commands = DatabaseCollection(type=ScheduledCommand, attribute="command")
    scheduler_interval = 3600
    scheduler = False
    callback_args = None
    chat_service = FakeChatService()

    def callback(self, *args):
        self.callback_args = args


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

    def test_quote_get_fresh_command(self):

        class FakeQuoteIsNotFresh(object):
            def is_fresh(self):
                return False

        class FakeQuoteIsFresh(object):
            def is_fresh(self):
                return True

            def __str__(self):
                return "I'm fresh"

        class FakeQuoteServiceLocal(object):

            def get_quote(self, ticker):
                if ticker == "not_fresh":
                    return FakeQuoteIsNotFresh()
                else:
                    return FakeQuoteIsFresh()

        factory = QuoteServiceFactory()
        factory.providers = {"fakeprovider": FakeQuoteServiceLocal}
        command = ["quote", "get_fresh", "fakeprovider", "not_fresh"]
        res = root_command.execute(*command, command_args={"service_factory": factory, "instance": self.ircbot})
        self.assertIsNone(res)

        command = ["quote", "get_fresh", "fakeprovider", "fresh"]
        res = root_command.execute(*command, command_args={"service_factory": factory, "instance": self.ircbot})
        self.assertEquals("I'm fresh", str(res))

    def test_quote_get_command_invalid_input(self):

        command = ["quote", "get", "invalid-provider", "aapl"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("No such provider 'invalid-provider'", res)

    def test_quote_search_command(self):

        command = ["quote", "search", "fakeprovider", "foobar"]
        res = self.__cmd_wrap(*command)
        self.assertIn("Ticker: FOO, Market: Foo Market, Name: Foo Company", res)

    def test_quote_search_command_invalid_input(self):

        command = ["quote", "search", "invalid-provider", "foobar"]
        res = self.__cmd_wrap(*command)
        self.assertIn("No such provider 'invalid-provider", res)

    def test_quote_search_command_none_type_response(self):

        command = ["quote", "search", "fakeprovider", "none-type-response"]
        res = self.__cmd_wrap(*command)
        self.assertIn("Response from provider 'fakeprovider' broken", res)

    def test_execute_help_command(self):

        command = ["help"]
        res = self.__cmd_wrap(*command)
        self.assertIn("quote (q) get <provider> <ticker>", res)
        self.assertIn("quote (q) search <provider> <ticker>", res)

    def test_execute_scheduler_ticker_commands(self):

        # blank state
        command = ["scheduler", "command", "get"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("No commands added", res)

        # add command
        command = ["scheduler", "command", "add", "quote", "get", "google", "foobar"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Added command: quote get google foobar", res)

        # add command again and fail gracefully
        command = ["scheduler", "command", "add", "quote", "get", "google", "foobar"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Command already in list", res)

        # verify command is there
        command = ["scheduler", "command", "get"]
        res = self.__cmd_wrap(*command)
        self.assertIn("Command: quote get google foobar", res)

        # remove command
        command = ["scheduler", "command", "remove", "quote", "get", "google", "foobar"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Removed command: quote get google foobar", res)

        # verify command is not there
        command = ["scheduler", "command", "get"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("No commands added", res)

        # remove it again and fail gracefully
        command = ["scheduler", "command", "remove", "quote", "get", "google", "foobar"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Command not in list", res)

    def test_execute_scheduler_interval_command(self):

        # default state
        command = ["scheduler", "interval", "get"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Interval: 3600 seconds", res)

        # update interval
        command = ["scheduler", "interval", "set", "60"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("New interval: 60 seconds", res)

        # get updated state
        command = ["scheduler", "interval", "get"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Interval: 60 seconds", res)

        # set garbage input
        command = ["scheduler", "interval", "set", "horseshit"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Can't set interval from garbage input, must be of an int", res)

    def test_execute_scheduler_toggle_command(self):

        command = ["scheduler", "enable"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Scheduler: enabled", res)
        self.assertTrue(self.ircbot.scheduler)

        command = ["scheduler", "disable"]
        res = self.__cmd_wrap(*command)
        self.assertEquals("Scheduler: disabled", res)
        self.assertFalse(self.ircbot.scheduler)

    def test_execute_fallback_command(self):

        command = ["hi", "stockbot"]
        res = self.__cmd_wrap(*command)
        self.assertIsNone(res)

    def test_quote_hints(self):
        command = ["quote", "hint", "list", "yahoo"]
        res = self.__cmd_wrap(*command)
        self.assertEqual("no hints found", res)

        command = ["quote", "hint", "add", "yahoo", "foo", "bar"]
        res = self.__cmd_wrap(*command)
        self.assertEqual("Added hint", res)

        command = ["quote", "hint", "list", "yahoo"]
        res = self.__cmd_wrap(*command)
        self.assertEqual(["Provider: yahoo, Ticker: foo, Free-text: bar"], res)

        command = ["quote", "hint", "remove", "yahoo", "foo"]
        res = self.__cmd_wrap(*command)
        self.assertEqual("Removed hint", res)

        command = ["quote", "hint", "remove", "yahoo", "foo"]
        res = self.__cmd_wrap(*command)
        self.assertEqual("No matching hint to remove", res)

        command = ["quote", "hint", "list", "yahoo"]
        res = self.__cmd_wrap(*command)
        self.assertEqual("no hints found", res)


class IntegrationTestCommand(unittest.TestCase):

    def setUp(self) -> None:
        create_tables()

    @unittest.skip
    @vcr.use_cassette('mock/vcr_cassettes/hints/yahoo.yaml')
    def test_quote_get_with_hints(self):

        def cmd_wrap(*command):
            return root_command.execute(*command, command_args={'service_factory': QuoteServiceFactory()})

        command = ["quote", "hint", "add", "yahoo", "INVE-B.ST", "investor", "b"]
        cmd_wrap(*command)

        command = ["quote", "get", "yahoo", "investor", "b"]
        res = cmd_wrap(*command)

        self.assertRegexpMatches(str(res), "^Name: Investor AB ser. B,.*")
