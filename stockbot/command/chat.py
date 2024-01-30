from . import root_command, Command, BlockingExecuteCommand, ProxyCommand

import logging

LOGGER = logging.getLogger(__name__)


def chat(*args, **kwargs):
    try:
        instance = kwargs.get('instance')
        message = " ".join(args[1:])
        response = instance.chat_service.say(message)
        return response
    except Exception as e:
        LOGGER.exception("chat failed")
        return "borken"


root_command.register_fallback(BlockingExecuteCommand(name="chat", execute_command=chat))
