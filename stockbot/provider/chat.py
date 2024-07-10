from g4f.client import Client
from g4f.cookies import set_cookies
from g4f.Provider import BingCreateImages, OpenaiChat, Gemini, Bing

import logging
import os
from datetime import datetime

LOGGER = logging.getLogger(__name__)

set_cookies(".bing.com", {
    "_U": os.getenv("COPILOT_COOKIE")
})


class ChatService(object):

    def __init__(self):
        self.client = Client(image_provider=BingCreateImages)
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
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=self.conversation_history,
            stream=False
        )
        self.conversation_history.append(dict(
            role='assistant',
            content=response
        ))
        return response.choices[0].message.content

    def image(self, prompt):
        response = self.client.images.generate(
            model="dall-e-3",
            prompt=prompt
        )
        return response.data[0].url
