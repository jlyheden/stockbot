import logging
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
