class BaseQuoteService(object):

    def get_quote(self, ticker):
        raise NotImplemented

    def search(self, query):
        raise NotImplemented


