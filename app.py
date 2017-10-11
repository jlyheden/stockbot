import os
import logging
import requests
import json

from irc.bot import SingleServerIRCBot
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr
import irc.client
import irc.strings

LOGGER = logging.getLogger(__name__)


class StockTickerMessage(object):

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


class StockChecker(object):

    indexes = {
        "omxs30": "https://www.bloomberg.com/markets/api/quote-page/OMX%3AIND?locale=en",
        "dax": "https://www.bloomberg.com/markets/api/quote-page/DAX%3AIND?locale=en"
    }

    def __init__(self, default_idx):
        self.default_idx = default_idx

    def get_default(self):
        return self.get(self.default_idx)

    def get(self, idx):
        try:
            url = self.indexes[idx]
            req = requests.get(url)
            if req.ok:
                j = json.loads(req.text)
                return StockTickerMessage(message=j)
        except Exception as e:
            LOGGER.exception("Failed to retrieve stock ticker")

    def add(self, name, url):
        self.indexes[name] = url

    def show_all(self):
        return "Indexes: {i}".format(i=",".join(["name={key} url={value}".format(key=key, value=value) for key, value in
                                                 self.indexes.items()]))


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
        self.stockchecker = StockChecker(default_idx)

    def stock_check_scheduler(self):
        resp = self.stockchecker.get_default()
        self.connection.privmsg(self.channel, str(resp))

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
                if irc.strings.lower(commands[0]) == "stock":

                    if irc.strings.lower(commands[1]) == "get":

                        idx = irc.strings.lower(commands[2])
                        msg = self.stockchecker.get(idx)
                        self.connection.privmsg(self.channel, str(msg))

                    elif irc.strings.lower(commands[1]) == "show":

                        self.connection.privmsg(self.channel, self.stockchecker.show_all())

                    elif irc.strings.lower(commands[1]) == "add":

                        name = irc.strings.lower(commands[2])
                        url = irc.strings.lower(commands[3])

                        self.stockchecker.add(name, url)
                        self.connection.privmsg(self.channel, "Added {name}".format(name=name))

                elif irc.strings.lower(commands[0]) == "help":

                    self.connection.privmsg(self.channel, "Usage: stock get <idx>       -- returns the data for <idx>")
                    self.connection.privmsg(self.channel, "Usage: stock show            -- returns list of idx available")
                    self.connection.privmsg(self.channel, "Usage: stock add <idx> <url> -- adds idx")

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
