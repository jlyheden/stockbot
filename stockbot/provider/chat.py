import g4f
import logging
from datetime import datetime

LOGGER = logging.getLogger(__name__)


class ChatService(object):

    def __init__(self):
        self.conversation_history = []
        self.conversation_start = None
        LOGGER.info("init the chat service")

    def say(self, msg):
        if not self.conversation_start:
            LOGGER.info("starting new conversation")
            self.conversation_start = datetime.now()
        elif (datetime.now() - self.conversation_start).seconds > 600:
            LOGGER.info("expiring old conversation")
            self.conversation_start = datetime.now()
            self.conversation_history.clear()
        self.conversation_history.append(dict(
            role='user',
            content=msg
        ))
        response = g4f.ChatCompletion.create(
            model="gpt-3.5-turbo",
            provider=g4f.Provider.Bing,
            messages=self.conversation_history,
            stream=False
        )
        self.conversation_history.append(dict(
            role='assistant',
            content=response
        ))
        return response
