import socket
import os
import logging
import time
import requests
import json
import re

from threading import Thread
from queue import Queue, Empty


LOGGER = logging.getLogger(__name__)


# Global message queue between cron and ircbot threads
QUEUE = Queue()

# TODO: move this to a database that can be manipulated via bot commands
IDX_MAPPER = {
    "omxs30": "https://www.bloomberg.com/markets/api/quote-page/OMX%3AIND?locale=en"
}


def get_stock_index(idx):
    try:
        url = IDX_MAPPER[idx]
        req = requests.get(url)
        if req.ok:
            return json.loads(req.text)
    except:
        LOGGER.error("Failed to retrieve ticker")


class Configuration(object):

    def __getattribute__(self, item):
        value = os.getenv(item.upper(), None)
        if value is None:
            raise RuntimeError("Must set environment variable {}".format(item.upper()))
        else:
            return value


class IRCMessage(object):

    @classmethod
    def factory(cls, *args, **kwargs):
        message = kwargs.get('message')
        message_split = message.split()

        if message_split[0] == "PING":
            return IRCPingMessage(ping_message=message_split[1])

        elif re.match(".* PRIVMSG .*#[^ ]+ .*", message):
            return IRCChannelMessage(sender=message_split[0], channel=message_split[2], message=message_split[3:])

        elif re.match("[^ ]+ [0-9]+ .*", message):
            return IRCStatusMessage(server=message_split[0], code=message_split[1], message=" ".join(message_split[3:]))

        else:
            return IRCUnknownMessage(message=message)

    def __str__(self):
        """We override str so that we can easily print debug what the hell we are creating"""
        return "{klass}: {attrs}".format(
            klass=type(self),
            attrs=",".join(
                ["{k}={v}".format(k=x, v=getattr(self, x))
                 for x in dir(self) if not callable(getattr(self, x)) and not x.startswith("__")
                 ])
        )


class IRCPingMessage(IRCMessage):

    def __init__(self, ping_message):
        self.ping_message = ping_message.lstrip(":")


class IRCStatusMessage(IRCMessage):

    def __init__(self, server, code, message):
        self.server = server
        self.code = int(code)
        self.message = message

    def is_ok(self):
        return self.code < 400


class IRCUnknownMessage(IRCMessage):

    def __init__(self, message):
        self.message = message


class IRCChannelMessage(IRCMessage):

    def __init__(self, sender, channel, message):
        self.sender = sender.split("!")[0].lstrip(":")
        self.channel = channel

        if message[0].endswith(":"):
            self.recipient = message[0].lstrip(":").rstrip(":")
            message.pop(0)
        else:
            self.recipient = None

        self.message = message


class IRCMessageResponses(object):

    def __init__(self, *args, **kwargs):
        self.messages = []

    def size(self):
        return len(self.messages)

    def is_empty(self):
        return len(self.messages) == 0

    def extend_from_raw(self, messages):
        self.messages.extend([IRCMessage.factory(message=x) for x in messages.decode().splitlines()])

    def __contains__(self, item):
        """
        Allows you to do:
        m = IRCMessageResponse(messages=b'bunch of irc messages')
        IRCPingMessage in m

        :param item:
        :return:
        """
        return item in [type(x) for x in self.messages]

    def get_of_type(self, t):
        return [x for x in self.messages if type(x) == t]


class IRCBot(Thread):

    buffersize = 2048

    def __init__(self, *args, **kwargs):
        super(IRCBot, self).__init__(name='ircbot_thread')
        self.server_name = kwargs.get('server_name')
        self.server_port = int(kwargs.get('server_port'))
        self.channel = kwargs.get('channel')
        self.nick = kwargs.get('nick')
        self.irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        LOGGER.info("Connecting to {s}:{p}".format(s=self.server_name, p=self.server_port))

        self.irc.connect((self.server_name, self.server_port))
        self.irc.setblocking(True)
        self.send_with_callback("NICK {}".format(self.nick), callback=self.pong_callback)
        self.send_with_callback("USER {} {} {} :I am bot {}".format(self.nick, self.nick, self.nick, self.nick),
                                callback=self.pong_callback)

        self.send_retry_until_callback("JOIN {}".format(self.channel), callback=self.until_ok_callback, retries=20)

    def send_retry_until_callback(self, msg, callback, retries=5):
        for i in range(retries):
            self.irc.setblocking(True)
            self.__irc_send_msg(msg)
            self.irc.setblocking(False)
            imr = IRCMessageResponses()
            for ii in range(5):
                try:
                    response = self.irc.recv(self.buffersize)
                    imr.extend_from_raw(response)
                except Exception as e:
                    pass
                time.sleep(1)
            if callback(imr):
                self.irc.setblocking(True)
                return
        raise RuntimeError("Failed to send command")

    def send_with_callback(self, msg, callback):
        self.__irc_send_msg(msg)
        self.irc.setblocking(False)
        imr = IRCMessageResponses()
        for i in range(5):
            try:
                response = self.irc.recv(self.buffersize)
                imr.extend_from_raw(response)
            except Exception as e:
                pass
            time.sleep(1)
        self.irc.setblocking(True)
        callback(imr)

    def until_ok_callback(self, imr):
        rv = []
        for m in imr.messages:
            LOGGER.debug(m)
            if type(m) is IRCStatusMessage:
                rv.append(m.is_ok())
        return False not in rv

    def pong_callback(self, imr):
        for m in imr.messages:
            LOGGER.debug(m)
            if type(m) is IRCPingMessage:
                self.send_pong(m.ping_message)

    def send_pong(self, p):
        self.__irc_send_msg("PONG {}".format(p))

    def send_channel_msg(self, m):
        self.__irc_send_msg("PRIVMSG {channel} :{message}".format(channel=self.channel, message=m))

    def __irc_send_msg(self, msg):
        self.irc.send("{}\r\n".format(msg).encode('utf-8'))

    def run(self):

        while True:
            try:
                self.connect()
            except ConnectionRefusedError:
                LOGGER.warning("Got connection refused, trying again real soon")
            else:
                break
            time.sleep(10)

        self.irc.setblocking(False)

        while True:

            LOGGER.debug("In the loop")
            # non block listen on messages
            try:
                messages = self.irc.recv(self.buffersize)
                imr = IRCMessageResponses()
                imr.extend_from_raw(messages=messages)
                self._msgs_handler(imr)
            except socket.error:
                pass

            # non block listen on work queue
            try:
                item = QUEUE.get(block=False)
                self.send_channel_msg(item)
            except Empty:
                pass

            time.sleep(1)

    def _msgs_handler(self, imr):

        for m in imr.messages:

            if type(m) is IRCPingMessage:
                self.send_pong(m.ping_message)
                continue

            if type(m) is IRCChannelMessage:

                if m.recipient == self.nick:

                    if m.message[0].lower() == "stock":
                        self.send_channel_msg("{sender}: i will support this one day".format(sender=m.sender))

                    else:
                        self.send_channel_msg("{sender}: {message} too".format(sender=m.sender,
                                                                               message=" ".join(m.message)))

                continue


class CronThread(Thread):

    def run(self):

        while True:
            values = get_stock_index("omxs30")
            price = values["basicQuote"]["price"]
            QUEUE.put("Current stock price for omxs30 is {price}".format(price=price))
            time.sleep(300)


if __name__ == '__main__':

    bot = IRCBot(server_name=Configuration().server_name, server_port=Configuration().server_port,
                 channel=Configuration().channel_name, nick=Configuration().nick)
    bot.start()

    #cron = CronThread()
    #cron.start()

    bot.join()
