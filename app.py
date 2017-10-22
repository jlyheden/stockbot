import logging
import os
from datetime import datetime

# import irc.client
import irc.strings
from irc.bot import SingleServerIRCBot
from irc.client import ip_numstr_to_quad

from stockbot.configuration import Configuration
from stockbot.db import create_tables
from stockbot.persistence import DatabaseCollection, ScheduledTicker
from stockbot.provider import root_command
from stockbot.provider.google import GoogleFinanceQueryService
from stockbot.util import colorify


# Set up logging
LOGLEVEL = os.getenv("LOGLEVEL", "info").upper()
logging.basicConfig(level=getattr(logging, LOGLEVEL),
                    format="%(asctime)s %(levelname)s %(module)s.%(funcName)s.%(filename)s:%(lineno)d : %(message)s")
LOGGER = logging.getLogger(__name__)


class ScheduleHandler(object):

    days = [1, 2, 3, 4, 5]
    hours = [9, 10, 11, 12, 13, 14, 15, 16, 17]

    def timer_should_execute(self, dt):
        """

        :param dt:
        :type dt: datetime
        :return:
        """
        return (dt.isoweekday() in self.days) and (dt.hour in self.hours)


class IRCBot(SingleServerIRCBot, ScheduleHandler):

    def __init__(self, channel, nickname, server, port, enable_scheduler=False):
        super(IRCBot, self).__init__([(server, int(port))], nickname, nickname)
        self.channel = channel

        self.scheduler = enable_scheduler
        self.reactor.scheduler.execute_every(60, self.stock_check_scheduler)
        self.quote_service = GoogleFinanceQueryService()
        self.tickers = DatabaseCollection(type=ScheduledTicker, attribute="ticker")
        self.scheduler_interval = 3600
        self.last_check = None

    def stock_check_scheduler(self):

        if not self.scheduler:
            LOGGER.debug("Scheduler is disabled")
            return

        now = datetime.now()

        if self.last_check is not None:
            if int(now.timestamp()) - self.last_check < self.scheduler_interval:
                return

        # TODO: not so configurable, fix
        if not self.timer_should_execute(now):
            return

        for ticker in self.tickers:
            resp = self.quote_service.get_quote(ticker)
            self.colorify_send(self.channel, str(resp))

        self.last_check = int(now.timestamp())

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)
        if os.path.exists("version.txt"):
            with open("version.txt", "r") as f:
                self.connection.privmsg(self.channel,
                                        "\x0306,13 I'M \x03\x0313,06 BACK! \x03\x0306 Running version\x03: \x0314{}\x03".
                                        format(f.read().strip()))

    def on_privmsg(self, c, e):
        pass

    def on_pubmsg(self, c, e):
        message = e.arguments[0]
        split = message.split(" ")
        to_me = split[0].endswith(":") and irc.strings.lower(split[0].rstrip(":")) == irc.strings.lower(
            self.connection.get_nickname())

        if to_me:

            commands = [irc.strings.lower(x) for x in split[1:]]
            root_command.execute(*commands, command_args={"service": self.quote_service, "instance": self},
                                 callback=self.command_callback)

    def command_callback(self, result):
        if isinstance(result, list):
            for row in result:
                self.colorify_send(self.channel, row)
        elif result is not None:
            self.colorify_send(self.channel, result)

    def colorify_send(self, target, msg):
        self.connection.privmsg(target, colorify(str(msg)))

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

    create_tables()

    bot = IRCBot(server=Configuration().server_name, port=Configuration().server_port,
                 channel=Configuration().channel_name, nickname=Configuration().nick,
                 enable_scheduler=Configuration().scheduler)
    bot.start()
