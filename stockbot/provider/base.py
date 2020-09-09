import logging

LOGGER = logging.getLogger(__name__)


class BaseQuoteService(object):

    def get_quote(self, ticker):
        raise NotImplemented

    def search(self, query):
        raise NotImplemented


class BaseQuote(object):

    def __str__(self):
        return self.fields_to_str(self.fields)

    def __getattribute__(self, item):
        try:
            # we cannot use this objects getattribute because then we loop until the world collapses
            return object.__getattribute__(self, item)
        except Exception as e:
            LOGGER.exception("Failed to look up attribute {}".format(item))
            return "N/A"

    def is_empty(self):
        try:
            return self.name == "N/A"
        except Exception:
            return True

    def is_fresh(self):
        return False

    @staticmethod
    def fields_to_str(fields):
        return ", ".join([
            "{k}: {v}".format(k=x[0], v=x[1]) for x in fields
        ])
