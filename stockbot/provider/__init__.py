import logging
from .ibindex import IbIndexQueryService
from .nasdaq import NasdaqIndexScraper, NasdaqCompany
from .google import StockDomain, GoogleFinanceQueryService
from .bloomberg import BloombergQueryService
from .avanza import AvanzaQueryService
from .ig import IGQueryService
from .yahoo import YahooQueryService
from stockbot.db import Base
from sqlalchemy import Column, String

LOGGER = logging.getLogger(__name__)


class ProviderHints(Base):
    __tablename__ = "provider_hints"
    provider = Column(String, primary_key=True)
    src = Column(String, primary_key=True)
    dst = Column(String)


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
        "bloomberg": BloombergQueryService,
        "avanza": AvanzaQueryService,
        "ig": IGQueryService,
        "ibindex": IbIndexQueryService,
        "yahoo": YahooQueryService
    }

    def get_service(self, name):
        if not hasattr(self, name):
            try:
                setattr(self, name, self.providers[name]())
            except KeyError as e:
                raise ValueError("provider '{}' not implemented".format(name))
        return getattr(self, name)
