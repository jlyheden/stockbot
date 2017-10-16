import sys

from stockbot.provider import GoogleFinanceQueryService
from stockbot.provider import root_command


def callback(result):
    if isinstance(result, list):
        print("\n".join(result))
    elif result is not None:
        print(result)
    else:
        root_command.execute(*["help"], callback=callback)

service = GoogleFinanceQueryService()

root_command.execute(*sys.argv[1:], command_args={"service": service}, callback=callback)
