import g4f
import logging
from datetime import datetime

LOGGER = logging.getLogger(__name__)


class ChatService(object):

    def __init__(self):
        self.conversation_history = []
        self.conversation_last_tz = None
        LOGGER.info("init the chat service")

    def say(self, msg):
        if self.conversation_last_tz and (datetime.now() - self.conversation_last_tz).seconds > 600:
            LOGGER.info("expiring old conversation")
            self.conversation_history.clear()
            self.conversation_history.append(dict(
                role='system',
                content='Respond professionally and helpfully. Provide concise and easy to understand answers. Do not use emoji characters in the response.'
            ))
        self.conversation_last_tz = datetime.now()
        self.conversation_history.append(dict(
            role='user',
            content=msg
        ))
        response = g4f.ChatCompletion.create(
            model="gpt-4-turbo",
            provider=g4f.Provider.Bing,
            messages=self.conversation_history,
            stream=False
        )
        self.conversation_history.append(dict(
            role='assistant',
            content=response
        ))
        return response
