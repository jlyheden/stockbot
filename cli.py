import sys
import logging

#logging.disable(logging.ERROR)

import stockbot.configuration
from stockbot.db import create_tables
from stockbot.provider import QuoteServiceFactory
from stockbot.command import root_command

stockbot.configuration.DEFAULT_VALUES["database_url"] = "sqlite:////cli.db"


def callback(result):
    if isinstance(result, list):
        print("\n".join(result))
    elif result is not None:
        print(result)
    else:
        root_command.execute(*["help"], callback=callback)


create_tables()

root_command.execute(*sys.argv[1:], command_args={"service_factory": QuoteServiceFactory()}, callback=callback)