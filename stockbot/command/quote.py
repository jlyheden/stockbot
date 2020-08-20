from . import root_command, Command, BlockingExecuteCommand, ProxyCommand
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
    lucky_args = ["avanza"]
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


quote_command = Command(name="quote", short_name="q")
quote_command.register(BlockingExecuteCommand(name="get", execute_command=get_quote, help="<provider> <ticker>"))
quote_command.register(BlockingExecuteCommand(name="get_fresh", execute_command=get_fresh_quote, help="<provider> <ticker>"))
quote_command.register(BlockingExecuteCommand(name="gl", execute_command=get_quote_lucky,
                                              help="<provider> <ticker>"))
quote_command.register(BlockingExecuteCommand(name="search", execute_command=search_quote,
                                              help="<provider> <ticker>"))

root_command.register(quote_command)
root_command.register(BlockingExecuteCommand(name="quick", short_name="qq", execute_command=get_quote_quick,
                                             help="<search-ticker-string>"))
root_command.register(ProxyCommand(name="qy", proxy_command=("quote", "get", "yahoo"), help="<ticker>"))
