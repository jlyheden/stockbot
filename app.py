import os
import logging
import requests
import json

from datetime import datetime
from urllib.parse import urlencode
from urllib.request import pathname2url
from irc.bot import SingleServerIRCBot
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr
import irc.client
import irc.strings

LOGGER = logging.getLogger(__name__)


class BloombergQuote(object):

    def __init__(self, *args, **kwargs):
        data = kwargs.get('message')
        for k, v in data["basicQuote"].items():
            setattr(self, k, v)
        self.marketstatus = data["marketStatus"]["marketStatus"]

    def __str__(self):
        if self.marketstatus == "ACTV":
            return "Name: {n}, Price: {p}, Open Price: {op}, Low Price: {lp}, High Price: {hp}, Percent Change 1 Day: {p1d}"\
                .format(n=self.name, p=self.price, op=self.openPrice, lp=self.lowPrice, hp=self.highPrice,
                        p1d=self.percentChange1Day)
        else:
            return "Name: {n} is closed".format(n=self.name)


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

    # search probably don't change that much, cache results
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

    def __init__(self, channel, nickname, server, port, default_idx="omxs30"):
        super(IRCBot, self).__init__([(server, int(port))], nickname, nickname)
        self.channel = channel

        # TODO: would be nice to be able to disable or reconfigure the scheduler from outside
        self.reactor.scheduler.execute_every(3600, self.stock_check_scheduler)
        self.quote_service = BloombergQueryService(default_idx)

    def stock_check_scheduler(self):
        now = datetime.now()
        # TODO: not so configurable, fix
        if now.isoweekday() not in [6, 7] and now.hour > 9 and (now.hour <= 17 and now.minute <= 30):
            resp = self.quote_service.get_default_quote()
            self.connection.privmsg(self.channel, str(resp))
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
                        self.connection.privmsg(self.channel, str(msg))

                    elif irc.strings.lower(commands[1]) == "search":

                        query = irc.strings.lower(commands[2])
                        msg = self.quote_service.search(query)
                        if msg.is_empty():
                            self.connection.privmsg(self.channel, "Nothing found for {query}".format(query=query))
                        else:
                            for m in msg.result_as_list():
                                self.connection.privmsg(self.channel, str(m))

                elif irc.strings.lower(commands[0]) == "help":

                    self.connection.privmsg(self.channel, "Usage: quote get <idx>      - returns the data for <idx>")
                    self.connection.privmsg(self.channel, "Usage: quote search <query> - returns list of idx available")

            except IndexError as e:
                self.connection.privmsg(self.channel, "Stack trace: {e}".format(e=e))

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

    def do_command(self, e, cmd):
        nick = e.source.nick
        c = self.connection

        cmd_split = cmd.split(" ")
        if cmd == "disconnect":
            self.disconnect()
        elif cmd == "die":
            self.die()
        elif cmd == "stats":
            for chname, chobj in self.channels.items():
                c.notice(nick, "--- Channel statistics ---")
                c.notice(nick, "Channel: " + chname)
                users = sorted(chobj.users())
                c.notice(nick, "Users: " + ", ".join(users))
                opers = sorted(chobj.opers())
                c.notice(nick, "Opers: " + ", ".join(opers))
                voiced = sorted(chobj.voiced())
                c.notice(nick, "Voiced: " + ", ".join(voiced))
        elif cmd == "dcc":
            dcc = self.dcc_listen()
            c.ctcp("DCC", nick, "CHAT chat %s %d" % (
                ip_quad_to_numstr(dcc.localaddress),
                dcc.localport))
        elif cmd_split[0].lower() == "stock":
            idx = cmd_split[1]
            resp = self.stockchecker.get(idx)
            self.connection.privmsg(self.channel, str(resp))
        else:
            c.notice(nick, "Not understood: " + cmd)


if __name__ == '__main__':

    bot = IRCBot(server=Configuration().server_name, port=Configuration().server_port,
                 channel=Configuration().channel_name, nickname=Configuration().nick)
    bot.start()
