from . import root_command, Command, BlockingExecuteCommand, NonBlockingExecuteCommand
from ..configuration import configuration
from requests import get
from requests.auth import HTTPBasicAuth
from libfi import StatisticsHelper
from libfi.util import TransactionJSONDecoder
import logging
import datetime
import json

LOGGER = logging.getLogger(__name__)


class Client(object):

    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.auth = HTTPBasicAuth(username, password)

    def get_fi_insider_transactions(self, d):
        response = get("{}/api/fi/insider/{}/transactions".format(self.base_url, d), auth=self.auth)
        response.raise_for_status()
        transactions = json.loads(response.text, cls=TransactionJSONDecoder)
        return transactions

    def get_top(self, d, t, venue):
        if venue:
            _url = "{}/api/fi/insider/{}/top-{}/{}".format(self.base_url, d, t, venue)
        else:
            _url = "{}/api/fi/insider/{}/top-{}".format(self.base_url, d, t)
        response = get(_url, auth=self.auth)
        response.raise_for_status()
        top_list = json.loads(response.text)
        return top_list

    @classmethod
    def factory(cls):
        return Client(base_url=configuration.lyheden_base_url, username=configuration.lyheden_username,
                      password=configuration.lyheden_password)


def insider_helper(t, response):
    if len(response) == 0:
        return "There were no {}s".format(t)
    else:
        return " | ".join(
            [
                "Person: {}, Company: {}, Position: {}, GAV: {}, Dates: {}, Sum: {}".format(x["person"],
                                                                                            x["instrument"],
                                                                                            x["position"],
                                                                                            x["gav"],
                                                                                            x["transaction_dates"],
                                                                                            x["value"])
                for x in response[0:3]
            ]
        )


def insider_top(*args, **kwargs):
    # Usage: <this> <type> <optional date> <optional venue>

    translation_table = {
        "buyer": "acquisition",
        "buyers": "acquisition",
        "seller": "disposal",
        "sellers": "disposal"
    }

    if len(args) == 0:
        return None

    try:
        check_date = args[1]
    except:
        check_date = datetime.datetime.now().date().isoformat()

    try:
        venue = args[2]
    except:
        venue = None

    transaction_type = translation_table.get(args[0], args[0])

    try:
        client = Client.factory()
        response = client.get_top(check_date, transaction_type, venue)
        result = insider_helper(transaction_type, response)
        return result
    except Exception as e:
        return "Failed: {}".format(e)


insider_command = Command(name="insider")
insider_command.register(BlockingExecuteCommand(name="top", execute_command=insider_top,
                                                help="<type: can be disposal, acquisition etc> <iso-date> <venue: can be nasdaq, first-north>"))
root_command.register(insider_command)
