from . import root_command, Command, BlockingExecuteCommand
import logging

LOGGER = logging.getLogger(__name__)


def get_quote(*args, **kwargs):
    provider = args[0]
    ticker = " ".join(args[1:])
    try:
        service = kwargs.get('service_factory').get_service(provider)
        return service.get_quote(ticker)
    except ValueError as e:
        LOGGER.exception("failed to retrieve service for provider '{}'".format(provider))
        return "No such provider '{}'".format(provider)


def get_fresh_quote(*args, **kwargs):
    provider = args[0]
    ticker = " ".join(args[1:])
    try:
        service = kwargs.get('service_factory').get_service(provider)
        ticker = service.get_quote(ticker)
        return ticker if ticker.is_fresh() else None
    except ValueError as e:
        LOGGER.exception("failed to retrieve service for provider '{}'".format(provider))
        return "No such provider '{}'".format(provider)


def get_quote_lucky(*args, **kwargs):
    """ some evil branching here, just want to get it to work though """
    provider = args[0]
    ticker = " ".join(args[1:])
    try:
        service = kwargs.get('service_factory').get_service(provider)
        response = service.get_quote(ticker)
        LOGGER.debug("Response from service get_quote: {}".format(str(response)))
        if response.is_empty():
            search_result = service.search(ticker)
            if search_result.is_empty():
                return "Nothing found for {}".format(ticker)
            else:
                first_ticker = [x for x in search_result.get_tickers() if x is not None][0]
                return service.get_quote(first_ticker)
        else:
            return response
    except ValueError as e:
        LOGGER.exception("failed to retrieve service for provider '{}'".format(provider))
        return "No such provider '{}'".format(provider)


def get_quote_quick(*args, **kwargs):
    lucky_args = ["bloomberg"]
    lucky_args.extend(args)
    return get_quote_lucky(*lucky_args, **kwargs)


def search_quote(*args, **kwargs):
    provider = args[0]
    ticker = " ".join(args[1:])
    try:
        service = kwargs.get('service_factory').get_service(provider)
        search_result = service.search(ticker)
        if search_result is None:
            return "Response from provider '{}' broken".format(provider)
        return search_result.result_as_list()
    except ValueError as e:
        LOGGER.exception("failed to retrieve service for provider '{}'".format(provider))
        return "No such provider '{}'".format(provider)


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

quote_command = Command(name="quote", short_name="q")
quote_command.register(BlockingExecuteCommand(name="get", execute_command=get_quote, help="<provider> <ticker>"))
quote_command.register(BlockingExecuteCommand(name="get_fresh", execute_command=get_fresh_quote, help="<provider> <ticker>"))
quote_command.register(BlockingExecuteCommand(name="gl", execute_command=get_quote_lucky,
                                              help="<provider> <ticker>"))
quote_command.register(BlockingExecuteCommand(name="search", execute_command=search_quote,
                                              help="<provider> <ticker>"))
quote_command.register(scheduler_command)

root_command.register(quote_command)
root_command.register(BlockingExecuteCommand(name="quick", short_name="qq", execute_command=get_quote_quick,
                                             help="<search-ticker-string>"))
