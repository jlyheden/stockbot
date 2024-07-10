from . import root_command, NonBlockingExecuteCommand

import logging

LOGGER = logging.getLogger(__name__)


def chat(*args, **kwargs):
    try:
        instance = kwargs.get('instance')
        message = " ".join(args[1:])
        response = instance.chat_service.say(message)
        response_list = []
        for line in response.split("\n"):
            more_lines = [line[i:i+512] for i in range(0, len(line), 512)]
            response_list.extend(more_lines)
        return response_list
    except Exception as e:
        LOGGER.exception("chat failed")
        return "FAIL '{}'".format(repr(e))


def image(*args, **kwargs):
    try:
        instance = kwargs.get('instance')
        prompt = " ".join(args[1:])
        response = instance.chat_service.image(prompt)
        return "Check this out: {}".format(response)
    except Exception as e:
        LOGGER.exception("image generation failed")
        return "FAIL '{}'".format(repr(e))


root_command.register(NonBlockingExecuteCommand(name="chat", execute_command=chat, exclusive=True))
root_command.register(NonBlockingExecuteCommand(name="image", execute_command=image, exclusive=True))
