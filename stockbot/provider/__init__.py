import logging
from .ibindex import IbIndexQueryService
from .yahoo import YahooQueryService
from stockbot.db import Base
from sqlalchemy import Column, String

LOGGER = logging.getLogger(__name__)


class ProviderHints(Base):
    __tablename__ = "provider_hints"
    provider = Column(String, primary_key=True)
    src = Column(String, primary_key=True)
    dst = Column(String)


class QuoteServiceFactory(object):

    providers = {
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
