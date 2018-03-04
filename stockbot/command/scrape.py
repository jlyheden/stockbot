from . import root_command, Command, BlockingExecuteCommand, NonBlockingExecuteCommand
import logging
import time
from sqlalchemy import func
from stockbot.db import Session
from stockbot.provider.nasdaq import NasdaqIndexScraper, NasdaqCompany
from stockbot.provider import StockDomain

LOGGER = logging.getLogger(__name__)


def nasdaq_scraper_task(*args, **kwargs):
    session = Session()
    nasdaq_scraper = NasdaqIndexScraper()
    try:
        session.query(NasdaqCompany).delete()
        session.commit()
    except Exception as e:
        LOGGER.exception("Failed to delete all records")
        session.rollback()
    else:
        try:
            rv = []
            for index in nasdaq_scraper.indexes.keys():
                rv.extend(nasdaq_scraper.scrape(index))
            session.add_all(rv)
            session.commit()
            return "Scraped {} companies from Nasdaq".format(len(rv))
        except Exception as e:
            LOGGER.exception("Failed to fetch and store nasdaq companies")
            session.rollback()
    finally:
        session.close()


def scrape_stats(*args, **kwargs):
    session = Session()
    result = session.query(NasdaqCompany.segment, func.count(NasdaqCompany.segment)).group_by(NasdaqCompany.segment)\
        .all()
    return "Scraped: {}".format(", ".join([
        "{k}={v}".format(k=x[0], v=x[1]) for x in result
    ]))


def stock_scrape_task(*args, **kwargs):
    currency = args[0].upper()
    segment = " ".join(args[1:])
    service = kwargs.get('service')
    session = Session()
    scraped = 0

    # TODO: not so pretty but what to do when there's no universal ticker naming scheme
    prefix_wrapper = {
        'SEK': 'STO'
    }
    prefix = prefix_wrapper.get(currency, None)

    try:
        result = session.query(NasdaqCompany.ticker)\
            .filter(NasdaqCompany.segment == segment)\
            .filter(NasdaqCompany.currency == currency)

        for r in result:

            # delete the record first if already existing
            try:
                session.query(StockDomain).filter(StockDomain.ticker == r.ticker).delete()
                session.commit()
            except Exception as e:
                LOGGER.exception("failed to delete stock ticker '{}'".format(r.ticker))
                session.rollback()

            # fetch the updated quote from interweb
            try:
                if prefix is not None:
                    ticker = "{}:{}".format(prefix, r.ticker)
                else:
                    ticker = r.ticker
                quote = service.get_quote(ticker)
                stock = StockDomain()
                stock.from_google_finance_quote(quote)
                session.add(stock)
                session.commit()
            except Exception as e:
                LOGGER.exception("failed to fetch and store stock ticker '{}'".format(r.ticker))
            else:
                scraped += 1

            # arbitrary sleep, avoid getting us blocked, rate-limited etc
            time.sleep(3)

    except Exception as e:
        LOGGER.exception("failed to scrape stocks")
        return "Failed to scrape stocks"
    else:
        return "Done scraping segment '{segment}' currency '{currency}' - scraped {scraped} companies".format(
            segment=segment, currency=currency, scraped=scraped)
    finally:
        session.close()


scrape_command = Command(name="scrape")
scrape_command.register(BlockingExecuteCommand(name="nasdaq", execute_command=nasdaq_scraper_task))
scrape_command.register(BlockingExecuteCommand(name="stats", execute_command=scrape_stats))
scrape_command.register(NonBlockingExecuteCommand(name="stocks", execute_command=stock_scrape_task, exclusive=True,
                        help="stocks <currency> <nasdaq-market-name>"))

root_command.register(scrape_command)
