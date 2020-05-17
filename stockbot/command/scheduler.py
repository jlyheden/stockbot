from . import root_command, Command, BlockingExecuteCommand
import logging

LOGGER = logging.getLogger(__name__)


def get_scheduler_command(*args, **kwargs):
    bot = kwargs.get('instance')
    if len(bot.commands) == 0:
        return "No commands added"
    return ["Command: {}".format(c) for c in bot.commands]


def add_scheduler_command(*args, **kwargs):
    command = " ".join(args)
    bot = kwargs.get('instance')
    if command in bot.commands:
        return "Command already in list"
    bot.commands.append(command)
    return "Added command: {}".format(command)


def remove_scheduler_command(*args, **kwargs):
    command = " ".join(args)
    bot = kwargs.get('instance')
    if command not in bot.commands:
        return "Command not in list"
    bot.commands.remove(command)
    return "Removed command: {}".format(command)


def get_scheduler_interval(*args, **kwargs):
    bot = kwargs.get('instance')
    return "Interval: {} seconds".format(bot.scheduler_interval)


def set_scheduler_interval(*args, **kwargs):
    bot = kwargs.get('instance')
    interval = args[0]
    try:
        bot.scheduler_interval = int(interval)
        return "New interval: {} seconds".format(interval)
    except ValueError as e:
        LOGGER.exception("Failed to convert int")
        return "Can't set interval from garbage input, must be of an int"


def enable_scheduler(*args, **kwargs):
    bot = kwargs.get('instance')
    bot.scheduler = True
    return "Scheduler: enabled"


def disable_scheduler(*args, **kwargs):
    bot = kwargs.get('instance')
    bot.scheduler = False
    return "Scheduler: disabled"


scheduler_command = Command(name="scheduler")
scheduler_command.register(BlockingExecuteCommand(name="enable", execute_command=enable_scheduler))
scheduler_command.register(BlockingExecuteCommand(name="disable", execute_command=disable_scheduler))

scheduler_command_command = Command(name="command")
scheduler_command_command.register(BlockingExecuteCommand(name="get", execute_command=get_scheduler_command))
scheduler_command_command.register(BlockingExecuteCommand(name="add", execute_command=add_scheduler_command,
                                                          help="<command>"))
scheduler_command_command.register(BlockingExecuteCommand(name="remove", execute_command=remove_scheduler_command,
                                                          help="<command>"))
scheduler_command.register(scheduler_command_command)

scheduler_interval_command = Command(name="interval")
scheduler_interval_command.register(BlockingExecuteCommand(name="get", execute_command=get_scheduler_interval))
scheduler_interval_command.register(BlockingExecuteCommand(name="set", execute_command=set_scheduler_interval,
                                                           help="<interval-int>"))
scheduler_command.register(scheduler_interval_command)

root_command.register(scheduler_command)
