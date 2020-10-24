from . import root_command, Command, BlockingExecuteCommand, ProxyCommand
from stockbot.db import Session
from stockbot.provider import ProviderHints
from sqlalchemy import and_
import logging

LOGGER = logging.getLogger(__name__)


def get_quote(*args, **kwargs):
    provider = args[0]
    ticker = " ".join(args[1:])
    session = None
    try:
        service = kwargs.get('service_factory').get_service(provider)
        session = Session()
        hint_ticker = session.query(ProviderHints).filter(and_(ProviderHints.provider == provider, ProviderHints.src == ticker))\
            .one_or_none()
        if hint_ticker:
            LOGGER.debug("Found hint ticker '{}' for ticker '{}', using that instead".format(hint_ticker, ticker))
            ticker = hint_ticker.dst
        return service.get_quote(ticker)
    except ValueError as e:
        LOGGER.exception("failed to retrieve service for provider '{}'".format(provider))
        return "No such provider '{}'".format(provider)
    finally:
        if session:
            session.close()


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


def add_quote_hint(*args, **kwargs):
    provider = args[0]
    dst_ticker = args[1]
    src_text = " ".join(args[2:])
    session = Session()
    try:
        hint = ProviderHints(provider=provider, src=src_text, dst=dst_ticker)
        session.add(hint)
        session.commit()
        return "Added hint"
    except Exception as e:
        LOGGER.exception("failed to add hint")
    finally:
        session.close()


def list_quote_hint(*args, **kwargs):
    provider = args[0]
    session = Session()
    try:
        result = []
        for hint in session.query(ProviderHints).filter(ProviderHints.provider == provider).all():
            result.append("Provider: {}, Ticker: {}, Free-text: {}".format(hint.provider, hint.dst, hint.src))
        if len(result) > 0:
            return result
        else:
            return "no hints found"
    except Exception as e:
        LOGGER.exception("failed to list hints")
        return "broken"
    finally:
        session.close()


def remove_quote_hint(*args, **kwargs):
    provider = args[0]
    dst_ticker = args[1]
    session = Session()
    try:
        hint = session.query(ProviderHints).filter(and_(ProviderHints.provider == provider, ProviderHints.dst == dst_ticker)).one_or_none()
        if hint:
            session.delete(hint)
            session.commit()
            return "Removed hint"
        else:
            return "No matching hint to remove"
    except Exception as e:
        LOGGER.exception("failed to remove hint")
    finally:
        session.close()


hint_command = Command(name="hint")
hint_command.register(BlockingExecuteCommand(name="add", execute_command=add_quote_hint,
                                             help="<provider> <dst-ticker> <free-text>"))
hint_command.register(BlockingExecuteCommand(name="remove", execute_command=remove_quote_hint,
                                             help="<provider> <dst-ticker>"))
hint_command.register(BlockingExecuteCommand(name="list", execute_command=list_quote_hint,
                                             help="<provider>"))


quote_command = Command(name="quote", short_name="q")
quote_command.register(BlockingExecuteCommand(name="get", execute_command=get_quote, help="<provider> <ticker>"))
quote_command.register(BlockingExecuteCommand(name="get_fresh", execute_command=get_fresh_quote, help="<provider> <ticker>"))
quote_command.register(BlockingExecuteCommand(name="gl", execute_command=get_quote_lucky,
                                              help="<provider> <ticker>"))
quote_command.register(BlockingExecuteCommand(name="search", execute_command=search_quote,
                                              help="<provider> <ticker>"))
quote_command.register(hint_command)

root_command.register(quote_command)
root_command.register(BlockingExecuteCommand(name="quick", short_name="qq", execute_command=get_quote_quick,
                                             help="<search-ticker-string>"))
root_command.register(ProxyCommand(name="qy", proxy_command=("quote", "get", "yahoo"), help="<ticker>"))
