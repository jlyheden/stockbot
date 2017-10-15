import os
import logging

from datetime import datetime
from irc.bot import SingleServerIRCBot
from irc.client import ip_numstr_to_quad
import irc.client
import irc.strings

from provider import root_command
from provider.google import GoogleFinanceQueryService

LOGLEVEL = os.getenv("LOGLEVEL", "info").upper()
logging.basicConfig(level=getattr(logging, LOGLEVEL),
                    format="%(asctime)s %(levelname)s %(module)s.%(filename)s.%(funcName)s:%(lineno)d : %(message)s")
LOGGER = logging.getLogger(__name__)

DEFAULT_VALUES = {
    "scheduler": "false"
}


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


class Configuration(object):

    def __getattr__(self, item):
        value = os.getenv(item.upper(), self.default_wrapper(item))
        if value is None:
            raise RuntimeError("Must set environment variable {}".format(item.upper()))
        else:
            if value.lower() in ["true", "false"]:
                return True if value.lower() == "true" else False
            return value

    @staticmethod
    def default_wrapper(item):

        if item in DEFAULT_VALUES:
            return DEFAULT_VALUES[item]
        return None


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
        self.tickers = []
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

    bot = IRCBot(server=Configuration().server_name, port=Configuration().server_port,
                 channel=Configuration().channel_name, nickname=Configuration().nick,
                 enable_scheduler=Configuration().scheduler)
    bot.start()
