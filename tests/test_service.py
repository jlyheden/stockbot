import unittest
import vcr
from stockbot.service.reddit import RedditFreeGamesService
from stockbot.db import create_tables, drop_tables, Session


class TestRedditFreeGamesService(unittest.TestCase):

    @vcr.use_cassette('mock/vcr_cassettes/reddit/freegames.yaml')
    def test_refresh(self):
        drop_tables()
        create_tables()
        with Session() as session:
            sut = RedditFreeGamesService()
            sut.refresh(session)
            games = sut.gimme(session)
            self.assertGreater(len(games), 0)

            games_again = sut.gimme(session)
            self.assertEquals(len(games_again), 0)

    @vcr.use_cassette('mock/vcr_cassettes/reddit/freegames.yaml')
    def test_refresh_with_ignore_words(self):
        drop_tables()
        create_tables()
        with Session() as session:
            sut = RedditFreeGamesService(ignore_words=["[PSA]", "gleam.io"])
            sut.refresh(session)
            games = sut.gimme(session)
            for game in games:
                self.assertNotIn("[PSA]", game.title)
                # dirty
                self.assertNotIn("[Steam] (Game) Combat Force", game.title)
