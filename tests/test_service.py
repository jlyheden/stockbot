import unittest
import vcr
from stockbot.service.reddit import RedditFreeGamesService
from stockbot.db import create_tables, Session


class TestRedditFreeGamesService(unittest.TestCase):

    def setUp(self):
        create_tables()

    @vcr.use_cassette('mock/vcr_cassettes/reddit/freegames.yaml')
    def test_refresh(self):
        with Session() as session:
            sut = RedditFreeGamesService()
            sut.refresh(session)
            games = sut.gimme(session)
            self.assertGreater(len(games), 0)

            games_again = sut.gimme(session)
            self.assertEquals(len(games_again), 0)
