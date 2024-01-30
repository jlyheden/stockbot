import sys
import logging

#logging.disable(logging.ERROR)

from stockbot.provider import QuoteServiceFactory
from stockbot.provider.chat import ChatService
from stockbot.command import root_command


class Fakebot:
    def __init__(self):
        self.chat_service = ChatService()


def callback(result):
    if isinstance(result, list):
        print("\n".join(result))
    elif result is not None:
        print(result)
    else:
        root_command.execute(*["help"], callback=callback)

bot = Fakebot()

root_command.execute(*sys.argv[1:], command_args={"service_factory": QuoteServiceFactory(), "instance": bot}, callback=callback)
