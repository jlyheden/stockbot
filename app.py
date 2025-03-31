import logging
import os
import sys
import signal
import types
import time
import ssl
from datetime import datetime

import irc.strings
from irc.bot import SingleServerIRCBot

from stockbot.configuration import configuration
from stockbot.db import create_tables
from stockbot.command import root_command
from stockbot.provider import QuoteServiceFactory
from stockbot.util import colorify


# Set up logging
LOGLEVEL = os.getenv("LOGLEVEL", "info").upper()
logging.basicConfig(level=getattr(logging, LOGLEVEL),
                    format="%(levelname)s %(module)s.%(funcName)s.%(filename)s:%(lineno)d : %(message)s")
LOGGER = logging.getLogger(__name__)


class IRCBot(SingleServerIRCBot):

    def __init__(self, **kwargs):
        super(IRCBot, self).__init__([(configuration.server_name, int(configuration.server_port),
                                       configuration.server_password)], configuration.nick, configuration.nick,
                                     **kwargs)
        self.channel = configuration.channel_name
        self.failed_health_checks = 0
        self.max_failed_health_checks = 10

        if configuration.scheduler:
            self.reactor.scheduler.execute_every(60, self.execute_every_60_seconds)
        if configuration.die_when_not_pinged:
            self.reactor.scheduler.execute_every(60, self.health_check)
        self.quote_service_factory = QuoteServiceFactory()
        self.ephemeral_oneshot_timers = set()
        self.last_server_ping = datetime.now()

        # self.commands = DatabaseCollection(type=ScheduledCommand, attribute="command")

    def health_check(self):
        if (datetime.now() - self.last_server_ping).seconds > int(configuration.die_when_not_pinged_in_s):
            self.die("BAI")

    def execute_every_60_seconds(self):
        if not self.connection.is_connected():
            LOGGER.debug("Not connected yet, hold off")
            return

        fired_timers = set()

        for timer in self.ephemeral_oneshot_timers:
            if timer.should_fire():
                try:
                    root_command.execute(*timer.command,
                                         command_args={"service_factory": self.quote_service_factory,
                                                       "instance": self}, callback=self.command_callback,
                                         callback_args={})
                except Exception as e:
                    LOGGER.exception("failed to execute scheduled command '{}'".format(timer.command))
                finally:
                    fired_timers.add(timer)

        for fired_timer in fired_timers:
          self.ephemeral_oneshot_timers.discard(fired_timer)

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def _startup_commands(self):
        # TODO: make configurable
        try:
            root_command.execute(*("game", "epic", "now"), command_args={"instance": self})
        except Exception as e:
            LOGGER.exception("startup commands failed", e)

    def on_welcome(self, c, e):
        c.join(self.channel)
        commit_hash = os.getenv("COMMIT_HASH", None)
        if commit_hash:
            self.connection.privmsg(self.channel,
                                    "\x0306,13 I'M \x03\x0313,06 BACK! \x03\x0306 commit\x03: \x0314{}\x03".
                                    format(commit_hash.strip()))
        self._startup_commands()

    def on_privmsg(self, c, e):
        sender = e.source.nick
        message = e.arguments[0]
        commands = [irc.strings.lower(x) for x in message.split(" ")]
        root_command.execute(*commands, command_args={"service_factory": self.quote_service_factory,
                                                      "instance": self, "sender": sender},
                             callback=self.command_callback_priv, callback_args={"sender": sender})

    def on_pubmsg(self, c, e):
        sender = e.source.nick
        my_nickname = irc.strings.lower(self.connection.get_nickname())
        message = e.arguments[0]
        nick_msg_split = message.split(":")
        respond = irc.strings.lower(nick_msg_split[0]) in [my_nickname, "{} (irc)".format(my_nickname)] and len(nick_msg_split) == 2

        if respond:
            commands = [irc.strings.lower(x) for x in nick_msg_split[1].split(" ") if len(x) > 0]
            try:
                root_command.execute(*commands, command_args={"service_factory": self.quote_service_factory,
                                                              "instance": self, "sender": sender},
                                     callback=self.command_callback, callback_args={"sender": sender})
            except Exception as e:
                LOGGER.exception("something failed", e)
                self.command_callback("something failed", sender=sender)

    def command_callback_priv(self, result, **kwargs):
        target = kwargs.get('sender', None)
        if isinstance(result, list) or isinstance(result, types.GeneratorType):
            for row in result:
                self.colorify_send(target, str(row))
                time.sleep(1)  # avoid getting kicked out from server
        elif result is not None:
            self.colorify_send(target, str(result))

    def command_callback(self, result, **kwargs):
        if isinstance(result, list) or isinstance(result, types.GeneratorType):
            for row in result:
                self.colorify_send(self.channel, str(row))
                time.sleep(1)  # avoid getting kicked out from server
        elif result is not None:
            self.colorify_send(self.channel, str(result))

    def colorify_send(self, target, msg):
        # irc.client.MessageTooLong: Messages limited to 512 bytes including CR/LF
        colored_message = colorify(msg)
        if len(colored_message) > 512:
            self.connection.privmsg(target, msg[:512])
        else:
            self.connection.privmsg(target, colored_message)

    def colorify_notice(self, target, msg):
        # irc.client.MessageTooLong: Messages limited to 512 bytes including CR/LF
        colored_message = colorify(msg)
        if len(colored_message) > 512:
            self.connection.notice(target, msg[:512])
        else:
            self.connection.notice(target, colored_message)

    def on_ping(self, c, e):
        self.last_server_ping = datetime.now()


if __name__ == '__main__':

    create_tables()

    kwargs = {}
    if configuration.server_use_ssl:
        ssl_factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
        kwargs["connect_factory"] = ssl_factory
    bot = IRCBot(**kwargs)

    def sigterm_handler(*args):
        bot.die("kthxbai")
        sys.exit(0)

    signal.signal(signal.SIGTERM, sigterm_handler)

    bot.start()
