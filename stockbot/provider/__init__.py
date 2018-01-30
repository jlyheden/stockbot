import logging
import time
import threading

from sqlalchemy import func
from stockbot.db import Session
from .nasdaq import NasdaqIndexScraper, NasdaqCompany
from .google import StockDomain, GoogleFinanceQueryService
from .bloomberg import BloombergQueryService

LOGGER = logging.getLogger(__name__)


class Analytics(object):

    def sort_by(self, c, attributes, reverse=False, max_results=None):
        result = sorted(c, key=lambda q: [getattr(q, x) for x in attributes], reverse=reverse)
        if isinstance(max_results, int):
            return result[:max_results]
        else:
            return result


class QuoteServiceFactory(object):

    providers = {
        "google": GoogleFinanceQueryService,
        "bloomberg": BloombergQueryService
    }

    def get_service(self, name):
        if not hasattr(self, name):
            try:
                setattr(self, name, self.providers[name]())
            except KeyError as e:
                raise ValueError("provider '{}' not implemented".format(name))
        return getattr(self, name)


class Command(object):

    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('name')
        self.short_name = kwargs.get('short_name', None)
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
        c = [x for x in self.subcommands if x.name == e or x.short_name == e]
        if len(c) == 0:
            return None
        return c[0].execute(*args[1:], **kwargs)

    def __repr__(self):
        if self.help is not None:
            return self.help
        else:
            if self.short_name is not None:
                return "{}({})".format(self.name, self.short_name)
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


class BlockingExecuteCommand(Command):

    def execute(self, *args, **kwargs):
        cb = kwargs.get('callback', None)
        cb_args = kwargs.get('callback_args', {})
        if callable(self.execute_command):
            result = self.execute_command(*args, **kwargs.get('command_args'))
        else:
            raise RuntimeError("execute_command not callable")
        if callable(cb):
            return cb(result, **cb_args)
        else:
            return result


class HelpCommand(Command):

    def execute(self, *args, **kwargs):
        cb = kwargs.get('callback', None)
        cb_args = kwargs.get('callback_args', {})
        # This is a bit smelly but couldn't get backtracking to work, even though Command.get_root(command)
        # had access to the root object it always returns None
        result = root_command.show_help()
        if callable(cb):
            return cb(result, **cb_args)
        else:
            return result


class NonBlockingExecuteCommand(Command):

    def __init__(self, *args, **kwargs):
        super(NonBlockingExecuteCommand, self).__init__(*args, **kwargs)
        self.exclusive = kwargs.get('exclusive', True)

    def execute(self, *args, **kwargs):
        cb = kwargs.get('callback', None)
        cb_args = kwargs.get('callback_args', {})
        thread_name = "thread-{}".format("_".join(args))
        if self.exclusive and self.is_already_running(thread_name):
            if callable(cb):
                return cb("Task is currently running, hold your horses")
            return "Task is currently running, hold your horses"
        if callable(self.execute_command):
            thread = CommandThread(name=thread_name, target=self.execute_command, args=args,
                                   kwargs=kwargs.get('command_args'), daemon=False)
            thread.set_callback(cb, cb_args)
            thread.start()
        else:
            raise RuntimeError("execute_command not callable")
        if callable(cb):
            return cb("Task started")
        return "Task started"

    @staticmethod
    def is_already_running(thread_name):
        return len([t for t in threading.enumerate() if t.name == thread_name]) > 0


#
# Thread wrapper
#
class CommandThread(threading.Thread):

    def __init__(self, *args, **kwargs):
        super(CommandThread, self).__init__(*args, **kwargs)
        self._callback = None
        self._callback_args = {}

    def set_callback(self, cb, cb_args):
        self._callback = cb
        self._callback_args = cb_args

    def run(self):
        # block until task has finished
        result = self._target(*self._args, **self._kwargs)

        if callable(self._callback):
            self._callback(result, **self._callback_args)


#
# Commands
#
def get_fundamental(*args, **kwargs):
    duration_mapper = {
        "y": "annual",
        "q": "recent_quarter"
    }
    ticker = args[0]
    try:
        duration = args[1]
        if duration not in ["y", "q"]:
            raise ValueError("duration must be y or q")
    except IndexError as e:
        LOGGER.exception("failed to parse arg")
        duration = "y"
    except ValueError as e:
        LOGGER.exception("failed to parse arg")
        duration = "y"

    # TODO: user provided provider
    service = kwargs.get('service_factory').get_service('google')
    return service.get_quote(ticker).fundamentals(duration_mapper[duration])


def get_quote(*args, **kwargs):
    provider = args[0]
    ticker = " ".join(args[1:])
    try:
        service = kwargs.get('service_factory').get_service(provider)
        return service.get_quote(ticker)
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


def search_quote(*args, **kwargs):
    provider = args[0]
    ticker = " ".join(args[1:])
    try:
        service = kwargs.get('service_factory').get_service(provider)
        return service.search(ticker).result_as_list()
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


def nasdaq_scraper_task(*args, **kwargs):
    session = Session()
    nasdaq_scraper = NasdaqIndexScraper()
    try:
        session.query(NasdaqCompany).delete()
        session.commit()
    except Exception as e:
        LOGGER.exception("Failed to delete all records")
        session.rollback()
    else:
        try:
            rv = []
            for index in nasdaq_scraper.indexes.keys():
                rv.extend(nasdaq_scraper.scrape(index))
            session.add_all(rv)
            session.commit()
            return "Scraped {} companies from Nasdaq".format(len(rv))
        except Exception as e:
            LOGGER.exception("Failed to fetch and store nasdaq companies")
            session.rollback()
    finally:
        session.close()


def scrape_stats(*args, **kwargs):
    session = Session()
    result = session.query(NasdaqCompany.segment, func.count(NasdaqCompany.segment)).group_by(NasdaqCompany.segment)\
        .all()
    return "Scraped: {}".format(", ".join([
        "{k}={v}".format(k=x[0], v=x[1]) for x in result
    ]))


def stock_scrape_task(*args, **kwargs):
    currency = args[0].upper()
    segment = " ".join(args[1:])
    service = kwargs.get('service')
    session = Session()
    scraped = 0

    # TODO: not so pretty but what to do when there's no universal ticker naming scheme
    prefix_wrapper = {
        'SEK': 'STO'
    }
    prefix = prefix_wrapper.get(currency, None)

    try:
        result = session.query(NasdaqCompany.ticker)\
            .filter(NasdaqCompany.segment == segment)\
            .filter(NasdaqCompany.currency == currency)

        for r in result:

            # delete the record first if already existing
            try:
                session.query(StockDomain).filter(StockDomain.ticker == r.ticker).delete()
                session.commit()
            except Exception as e:
                LOGGER.exception("failed to delete stock ticker '{}'".format(r.ticker))
                session.rollback()

            # fetch the updated quote from interweb
            try:
                if prefix is not None:
                    ticker = "{}:{}".format(prefix, r.ticker)
                else:
                    ticker = r.ticker
                quote = service.get_quote(ticker)
                stock = StockDomain()
                stock.from_google_finance_quote(quote)
                session.add(stock)
                session.commit()
            except Exception as e:
                LOGGER.exception("failed to fetch and store stock ticker '{}'".format(r.ticker))
            else:
                scraped += 1

            # arbitrary sleep, avoid getting us blocked, rate-limited etc
            time.sleep(3)

    except Exception as e:
        LOGGER.exception("failed to scrape stocks")
        return "Failed to scrape stocks"
    else:
        return "Done scraping segment '{segment}' currency '{currency}' - scraped {scraped} companies".format(
            segment=segment, currency=currency, scraped=scraped)
    finally:
        session.close()


def stock_analytics_fields(*args, **kwargs):
    fields = ", ".join(StockDomain.__table__.columns._data.keys())
    LOGGER.debug("Fields for StockDomain: {}".format(fields))
    return "Fields: {}".format(fields)


def stock_analytics_top(*args, **kwargs):
    rv = []

    if len(args) < 2:
        return ["Error: need moar args"]

    try:
        count = int(args[0])
    except ValueError:
        rv.append("Error: {} is not a number sherlock".format(args[0]))
        count = 5

    try:
        sort_field_name = args[1]
        filter_by = getattr(StockDomain, sort_field_name)
    except AttributeError:
        return ["Error: '{}' is not a valid field".format(args[1])]

    sort_descending = len(args) == 3 and args[2] == "desc"
    session = Session()

    if sort_descending:
        tmp = getattr(StockDomain, sort_field_name)
        order_by = getattr(tmp, "desc")()
    else:
        order_by = filter_by

    try:
        result = session.query(StockDomain)\
            .filter(filter_by != 0.0)\
            .order_by(order_by).limit(count)
        rv.extend(["Top {}: Ticker: {}, Name: {}, Value: {}".format(i + 1, x.ticker, x.name, getattr(x, sort_field_name))
                   for i, x in enumerate(result)])
    except Exception as e:
        LOGGER.exception("failed to query stockdomain for top '{}'".format(sort_field_name))
    finally:
        session.close()
        if len(rv) == 0:
            rv.append("Nothing found")
        return rv


#
# Register the command tree
#
scheduler_command_command = Command(name="command")
scheduler_command_command.register(BlockingExecuteCommand(name="get", execute_command=get_scheduler_command))
scheduler_command_command.register(BlockingExecuteCommand(name="add", execute_command=add_scheduler_command,
                                                          help="add <command>"))
scheduler_command_command.register(BlockingExecuteCommand(name="remove", execute_command=remove_scheduler_command,
                                                          help="remove <command>"))

scheduler_interval_command = Command(name="interval")
scheduler_interval_command.register(BlockingExecuteCommand(name="get", execute_command=get_scheduler_interval))
scheduler_interval_command.register(BlockingExecuteCommand(name="set", execute_command=set_scheduler_interval,
                                                           help="set <interval-int>"))

scheduler_command = Command(name="scheduler")
scheduler_command.register(scheduler_command_command)
scheduler_command.register(scheduler_interval_command)
scheduler_command.register(BlockingExecuteCommand(name="enable", execute_command=enable_scheduler))
scheduler_command.register(BlockingExecuteCommand(name="disable", execute_command=disable_scheduler))

quote_command = Command(name="quote", short_name="q")
quote_command.register(BlockingExecuteCommand(name="get", execute_command=get_quote, help="get <provider> <ticker>"))
quote_command.register(BlockingExecuteCommand(name="gl", execute_command=get_quote_lucky,
                                              help="gl <provider> <ticker>"))
quote_command.register(BlockingExecuteCommand(name="search", execute_command=search_quote,
                                              help="search <provider> <ticker>"))
quote_command.register(scheduler_command)

fundamental_command = Command(name="fundamental", short_name="fa")
fundamental_command.register(BlockingExecuteCommand(name="get", execute_command=get_fundamental,
                                                    help="get <ticker> <q|y>"))
fundamental_command.register(BlockingExecuteCommand(name="fields", execute_command=stock_analytics_fields))
fundamental_command.register(BlockingExecuteCommand(name="top", execute_command=stock_analytics_top,
                                                    help="top <count> <field> (optional 'desc')"))

scrape_command = Command(name="scrape")
scrape_command.register(BlockingExecuteCommand(name="nasdaq", execute_command=nasdaq_scraper_task))
scrape_command.register(BlockingExecuteCommand(name="stats", execute_command=scrape_stats))
scrape_command.register(NonBlockingExecuteCommand(name="stocks", execute_command=stock_scrape_task, exclusive=True,
                        help="stocks <currency> <nasdaq-market-name>"))

root_command = Command(name="root")
root_command.register(quote_command)
root_command.register(fundamental_command)
root_command.register(scrape_command)
root_command.register(HelpCommand(name="help"))
