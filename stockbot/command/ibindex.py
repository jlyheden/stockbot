from . import root_command, Command, BlockingExecuteCommand
import logging

LOGGER = logging.getLogger(__name__)


def search(*args, **kwargs):
    if len(args) == 0:
        return None
    search_text = args[0]
    service = kwargs.get('service_factory').get_service("ibindex")
    try:
        search_result = service.search(search_text)
        return search_result.result_as_list()
    except Exception as e:
        LOGGER.exception("failed to query service")
        return "Broken because of: {}".format(e)


def get(*args, **kwargs):
    if len(args) == 0:
        return None
    search_text = args[0]
    service = kwargs.get('service_factory').get_service("ibindex")
    try:
        search_result = service.search(search_text)
        ticker = search_result.get_ranked_ticker()
        quote_result = service.get_quote(ticker)
        return quote_result
    except Exception as e:
        LOGGER.exception("failed to query service")
        return "Broken because of: {}".format(e)


ibindex_command = Command(name="ibindex")
ibindex_command.register(BlockingExecuteCommand(name="search", execute_command=search, help="<text>",
                                                expected_num_args=1))
ibindex_command.register(BlockingExecuteCommand(name="get", execute_command=get, help="<text>", expected_num_args=1))

root_command.register(ibindex_command)
