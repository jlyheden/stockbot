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
        response = get("{}/api/fi/insider/{}.json".format(self.base_url, d), auth=self.auth)
        response.raise_for_status()
        transactions = json.loads(response.text, cls=TransactionJSONDecoder)
        return transactions

    @classmethod
    def factory(cls):
        return Client(base_url=configuration.lyheden_base_url, username=configuration.lyheden_username,
                      password=configuration.lyheden_password)


def insider_top_buyer(*args, **kwargs):
    if len(args) == 0:
        check_date = datetime.datetime.now().date().isoformat()
    else:
        check_date = args[0]
    client = Client.factory()
    transactions = client.get_fi_insider_transactions(check_date)
    helper = StatisticsHelper(transactions, ignore_venues=["Outside a trading venue", "NORDIC SME"])
    result = helper.get_top_buyers_by_company(limit=1)
    return "Company: {}, Total Amount: {} SEK".format(result[0][0], result[0][1])


def insider_top_seller(*args, **kwargs):
    if len(args) == 0:
        check_date = datetime.datetime.now().date().isoformat()
    else:
        check_date = args[0]
    client = Client.factory()
    transactions = client.get_fi_insider_transactions(check_date)
    helper = StatisticsHelper(transactions, ignore_venues=["Outside a trading venue", "NORDIC SME"])
    result = helper.get_top_sellers_by_company(limit=1)
    return "Company: {}, Total Amount: {} SEK".format(result[0][0], result[0][1])


insider_command = Command(name="insider")
insider_command.register(BlockingExecuteCommand(name="top-buyer", execute_command=insider_top_buyer, help="<iso-date>"))
insider_command.register(BlockingExecuteCommand(name="top-seller", execute_command=insider_top_seller, help="<iso-date>"))
root_command.register(insider_command)
