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


root_command.register_fallback(BlockingExecuteCommand(name="chat", execute_command=chat))
