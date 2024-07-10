from . import root_command, Command, BlockingExecuteCommand, ProxyCommand

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
        return "borken"


def image(*args, **kwargs):
    try:
        instance = kwargs.get('instance')
        prompt = " ".join(args[1:])
        response = instance.chat_service.image(prompt)
        return "Check this out: {}".format(response)
    except Exception as e:
        LOGGER.exception("image generation failed")
        return "borken"


root_command.register(BlockingExecuteCommand(name="chat", execute_command=chat))
root_command.register(BlockingExecuteCommand(name="image", execute_command=image))
