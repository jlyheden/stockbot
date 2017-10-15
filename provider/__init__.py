import logging

LOGGER = logging.getLogger(__name__)


class Analytics(object):

    def sort_by(self, c, attributes, reverse=False, max_results=None):
        result = sorted(c, key=lambda q: [getattr(q, x) for x in attributes], reverse=reverse)
        if isinstance(max_results, int):
            return result[:max_results]
        else:
            return result


class Command(object):

    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('name')
        self.execute_command = kwargs.get('execute_command')
        self.help = kwargs.get('help', None)
        self.parent_command = None
        self.subcommands = []

    def register(self, command):
        command.parent_command = self
        self.subcommands.append(command)

    def execute(self, *args, **kwargs):
        """
        Recurse the command tree, this method should be overridden when it actually should be doing something

        :param args:
        :return:
        """
        e = args[0]
        LOGGER.debug("Item: {}".format(e))
        c = [x for x in self.subcommands if x.name == e]
        if len(c) == 0:
            return None
        return c[0].execute(*args[1:], **kwargs)

    def __repr__(self):
        if self.help is not None:
            return self.help
        else:
            return self.name

    def show_help(self):
        def paths(tree):
            """took and modified https://stackoverflow.com/a/5671568"""
            root = tree
            rooted_paths = [[root]]
            for subtree in tree.subcommands:
                useable = paths(subtree)
                for path in useable:
                    if len(path[-1].subcommands) == 0:
                        rooted_paths.append([root] + path)
            return rooted_paths
        rv = []
        for c in paths(self)[1:]:
            rv.append(" ".join([str(x) for x in c[1:]]))
        return rv

    @staticmethod
    def get_root(command):
        """can reach root command but always returns None for some reason"""
        if command.parent_command is None:
            print("Got command {}".format(command))
            print(command.show_help())
            return command
        Command.get_root(command.parent_command)


class ExecuteCommand(Command):

    def execute(self, *args, **kwargs):
        cb = kwargs.get('callback', None)
        if callable(self.execute_command):
            result = self.execute_command(*args, **kwargs.get('command_args'))
        else:
            raise RuntimeError("execute_command not callable")
        if callable(cb):
            return cb(result)
        else:
            return result


class HelpCommand(Command):

    def execute(self, *args, **kwargs):
        cb = kwargs.get('callback', None)
        # This is a bit smelly but couldn't get backtracking to work, even though Command.get_root(command)
        # had access to the root object it always returns None
        result = root_command.show_help()
        if callable(cb):
            return cb(result)
        else:
            return result


#
# Commands
#
def get_fundamental(*args, **kwargs):
    ticker = " ".join(args)
    service = kwargs.get('service')
    return service.get_quote(ticker).fundamentals()


def get_quote(*args, **kwargs):
    ticker = " ".join(args)
    service = kwargs.get('service')
    return service.get_quote(ticker)


def search_quote(*args, **kwargs):
    ticker = " ".join(args)
    service = kwargs.get('service')
    result = service.search(ticker)
    return result.result_as_list()


def get_scheduler_ticker(*args, **kwargs):
    bot = kwargs.get('instance')
    if len(bot.tickers) == 0:
        return "No tickers added"
    return "Tickers: {t}".format(t=",".join(bot.tickers))


def add_scheduler_ticker(*args, **kwargs):
    ticker = " ".join(args)
    bot = kwargs.get('instance')
    if ticker in bot.tickers:
        return "Ticker already in list"
    bot.tickers.append(ticker)
    return "Added ticker: {}".format(ticker)


def remove_scheduler_ticker(*args, **kwargs):
    ticker = " ".join(args)
    bot = kwargs.get('instance')
    if ticker not in bot.tickers:
        return "Ticker not in list"
    bot.tickers.remove(ticker)
    return "Removed ticker: {}".format(ticker)


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

#
# Register the command tree
#

scheduler_tickers_command = Command(name="tickers")
scheduler_tickers_command.register(ExecuteCommand(name="get", execute_command=get_scheduler_ticker))
scheduler_tickers_command.register(ExecuteCommand(name="add", execute_command=add_scheduler_ticker,
                                                  help="add <ticker>"))
scheduler_tickers_command.register(ExecuteCommand(name="remove", execute_command=remove_scheduler_ticker,
                                                  help="remove <ticker>"))

scheduler_interval_command = Command(name="interval")
scheduler_interval_command.register(ExecuteCommand(name="get", execute_command=get_scheduler_interval))
scheduler_interval_command.register(ExecuteCommand(name="set", execute_command=set_scheduler_interval,
                                                   help="set <interval-int>"))

scheduler_command = Command(name="scheduler")
scheduler_command.register(scheduler_tickers_command)
scheduler_command.register(scheduler_interval_command)
scheduler_command.register(ExecuteCommand(name="enable", execute_command=enable_scheduler))
scheduler_command.register(ExecuteCommand(name="disable", execute_command=disable_scheduler))

quote_command = Command(name="quote")
quote_command.register(ExecuteCommand(name="get", execute_command=get_quote, help="get <ticker>"))
quote_command.register(ExecuteCommand(name="search", execute_command=search_quote, help="search <ticker>"))
quote_command.register(scheduler_command)

fundamental_command = Command(name="fundamental")
fundamental_command.register(ExecuteCommand(name="get", execute_command=get_fundamental, help="get <ticker>"))

root_command = Command(name="root")
root_command.register(quote_command)
root_command.register(fundamental_command)
root_command.register(HelpCommand(name="help"))
