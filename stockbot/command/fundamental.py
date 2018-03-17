from . import root_command, Command, BlockingExecuteCommand
from stockbot.provider import StockDomain
from stockbot.db import Session
import logging

LOGGER = logging.getLogger(__name__)


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
        rv.extend(["Top {}: Ticker: {}, Name: {}, Value: {}".format(i + 1, x.ticker, x.name,
                                                                    getattr(x, sort_field_name))
                   for i, x in enumerate(result)])
    except Exception as e:
        LOGGER.exception("failed to query stockdomain for top '{}'".format(sort_field_name))
    finally:
        session.close()
        if len(rv) == 0:
            rv.append("Nothing found")
        return rv


fundamental_command = Command(name="fundamental", short_name="fa")
fundamental_command.register(BlockingExecuteCommand(name="get", execute_command=get_fundamental, help="<ticker> <q|y>"))
fundamental_command.register(BlockingExecuteCommand(name="fields", execute_command=stock_analytics_fields))
fundamental_command.register(BlockingExecuteCommand(name="top", execute_command=stock_analytics_top,
                                                    help="<count> <field> (optional 'desc')"))

root_command.register(fundamental_command)
