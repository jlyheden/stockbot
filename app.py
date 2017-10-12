import os
import logging
import requests
import json

from datetime import datetime
from urllib.parse import urlencode
from urllib.request import pathname2url
from irc.bot import SingleServerIRCBot
from irc.client import ip_numstr_to_quad
import irc.client
import irc.strings

LOGLEVEL = os.getenv("LOGLEVEL", "info").upper()
logging.basicConfig(level=getattr(logging, LOGLEVEL),
                    format="%(asctime)s %(levelname)s %(module)s.%(filename)s.%(funcName)s:%(lineno)d : %(message)s")
LOGGER = logging.getLogger(__name__)


def colorify(msg):

    # split over comma separated "sections"
    section_split = msg.split(",")

    rv = []

    for section in section_split:

        # split over subject : value
        s_split = section.split(":", 1)

        # there was no subject, just color everything grey
        if len(s_split) == 1:
            s_replace = "\x0314{}\x03".format(s_split[0])

        # we identified subject : value
        else:
            try:

                # if value is a number
                v = float(s_split[1])

                # negative gets colored red
                if v < 0:
                    value_replace = "\x0304{}\x03".format(s_split[1])

                # positive gets colored green
                else:
                    value_replace = "\x0303{}\x03".format(s_split[1])

            except ValueError as e:

                # a non-number gets colored grey
                value_replace = "\x0314{}\x03".format(s_split[1])
            finally:
                s_replace = "\x0306{k}\x03:{v}".format(k=s_split[0], v=value_replace)

        # append the result into a list
        rv.append(s_replace)

    # sew the list together into a string again
    return "\x0300,\x03".join(rv)


class BloombergQuote(object):

    def __init__(self, *args, **kwargs):
        data = kwargs.get('message')
        for k, v in data["basicQuote"].items():
            if k == "lastUpdateEpoch":
                try:
                    setattr(self, "lastUpdateDatetime", datetime.fromtimestamp(int(v)).strftime("%Y-%m-%d %H:%M:%S"))
                except Exception as e:
                    LOGGER.exception("Failed to create attribute from lastUpdateEpoch")
            setattr(self, k, v)

    def __str__(self):
        return "Name: {n}, Price: {p}, Open Price: {op}, Low Price: {lp}, High Price: {hp}, Percent Change 1 Day: {p1d}, Update Time: {ut}"\
            .format(n=self.name, p=self.price, op=self.openPrice, lp=self.lowPrice, hp=self.highPrice,
                    p1d=self.percentChange1Day, ut=self.lastUpdateDatetime)

    def __getattribute__(self, item):
        try:
            # we cannot use this objects getattribute because then we loop until the world collapses
            return object.__getattribute__(self, item)
        except Exception as e:
            LOGGER.exception("Failed to look up attribute {}".format(item))
            return "N/A"

    def is_market_open(self):
        """
        Have to pick self.userTimeZone, self.nyTradeStartTime and self.nyTradeEndTime
        Parse the funky freeform time format into epoch
        Get time of now in timezone
        Compare if now in timezone is more than starttime and less than endtime
        TODO: fix some other time
        :return:
        """
        pass


class BloombergSearchResult(object):

    def __init__(self, *args, **kwargs):
        self.result = kwargs.get('result')["results"]

    def __str__(self):
        return "Result: {r}".format(r=" | ".join(
            ["Ticker: {t}, Country: {c}, Name: {n}, Type: {tt}".format(t=x["ticker_symbol"], c=x["country"],
                                                                       n=x["name"], tt=x["resource_type"])
             for x in self.result
             ]
        ))

    def result_as_list(self):
        return ["Ticker: {t}, Country: {c}, Name: {n}, Type: {tt}".format(t=x["ticker_symbol"], c=x["country"],
                                                                          n=x["name"], tt=x["resource_type"])
                for x in self.result
                ]

    def is_empty(self):
        return len(self.result) == 0


class BloombergQueryService(object):

    # search results probably don't change that much so cache them
    search_cache = {}

    def __init__(self, default_ticker):
        self.default_ticker = default_ticker

    def get_default_quote(self):
        return self.get_quote(self.default_ticker)

    def get_quote(self, ticker):
        try:
            url = self.__quote_url(ticker)
            req = requests.get(url)
            if req.ok:
                j = json.loads(req.text)
                return BloombergQuote(message=j)
        except Exception as e:
            LOGGER.exception("Failed to retrieve stock quote")
            return None

    def search(self, query):
        if query not in self.search_cache:
            LOGGER.info("Response from query {q} not in cache, will query bloombergs search api".format(q=query))
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
                return BloombergSearchResult(result=j)
            else:
                raise Exception("Failed to query bloomberg search api. Code: {c}, Text: {t}".format(c=req.status_code,
                                                                                                    t=req.text))
        except Exception as e:
            LOGGER.exception("Failed to search for {q}, search url: {u}".format(q=query, u=url))
            raise

    def __quote_url(self, ticker):
        params = {
            "locale": "en"
        }
        path = "/markets/api/quote-page/{}".format(ticker)
        url = "https://www.bloomberg.com{path}?{params}".format(path=pathname2url(path), params=urlencode(params))
        LOGGER.debug("quote_url: {}".format(url))
        return url

    def __search_url(self, query):
        params = {
            "sites": "bbiz",
            "query": query
        }
        url = "https://search.bloomberg.com/lookup.json?{params}".format(params=urlencode(params))
        LOGGER.debug("search url: {}".format(url))
        return url


class Configuration(object):

    def __getattribute__(self, item):
        value = os.getenv(item.upper(), None)
        if value is None:
            raise RuntimeError("Must set environment variable {}".format(item.upper()))
        else:
            return value


class IRCBot(SingleServerIRCBot):

    def __init__(self, channel, nickname, server, port, default_ticker):
        super(IRCBot, self).__init__([(server, int(port))], nickname, nickname)
        self.channel = channel

        # TODO: would be nice to be able to disable or reconfigure the scheduler from outside
        self.reactor.scheduler.execute_every(3600, self.stock_check_scheduler)
        self.quote_service = BloombergQueryService(default_ticker)

    def stock_check_scheduler(self):
        now = datetime.now()
        # TODO: not so configurable, fix
        if now.isoweekday() not in [6, 7] and now.hour > 9 and (now.hour <= 17 and now.minute <= 30):
            resp = self.quote_service.get_default_quote()
            self.colorify_send(self.channel, str(resp))
        else:
            LOGGER.debug("Ignoring notifications since stock market is not open")

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_privmsg(self, c, e):
        pass

    def on_pubmsg(self, c, e):
        message = e.arguments[0]
        split = message.split(" ")
        to_me = split[0].endswith(":") and irc.strings.lower(split[0].rstrip(":")) == irc.strings.lower(
            self.connection.get_nickname())

        #
        # TODO: fugly, can we avoid this spaghetti mess?
        #
        if to_me:

            # strip nick from message
            commands = split[1:]

            try:
                if irc.strings.lower(commands[0]) == "quote":

                    if irc.strings.lower(commands[1]) == "get":

                        idx = irc.strings.lower(commands[2])
                        msg = self.quote_service.get_quote(idx)
                        self.colorify_send(self.channel, str(msg))

                    elif irc.strings.lower(commands[1]) == "search":

                        query = irc.strings.lower(commands[2])
                        msg = self.quote_service.search(query)
                        if msg.is_empty():
                            self.colorify_send(self.channel, "Nothing found for {query}".format(query=query))
                        else:
                            for m in msg.result_as_list():
                                self.colorify_send(self.channel, str(m))

                elif irc.strings.lower(commands[0]) == "help":

                    self.colorify_send(self.channel, "Usage: quote get <ticker>   - returns the data for <ticker>")
                    self.colorify_send(self.channel, "Usage: quote search <query> - returns list of tickers available")

            except IndexError as e:
                self.connection.privmsg(self.channel, "Stack trace: {e}".format(e=e))

    def colorify_send(self, target, msg):
        self.connection.privmsg(target, colorify(msg))

    def on_dccmsg(self, c, e):
        # non-chat DCC messages are raw bytes; decode as text
        text = e.arguments[0].decode('utf-8')
        c.privmsg("You said: " + text)

    def on_dccchat(self, c, e):
        if len(e.arguments) != 2:
            return
        args = e.arguments[1].split()
        if len(args) == 4:
            try:
                address = ip_numstr_to_quad(args[2])
                port = int(args[3])
            except ValueError:
                return
            self.dcc_connect(address, port)


if __name__ == '__main__':

    bot = IRCBot(server=Configuration().server_name, port=Configuration().server_port,
                 channel=Configuration().channel_name, nickname=Configuration().nick,
                 default_ticker=Configuration().default_ticker)
    bot.start()
