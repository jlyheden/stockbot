import unittest

from stockbot.db import create_tables
from stockbot.persistence import DatabaseCollection, ScheduledTicker


class TestDatabaseCollection(unittest.TestCase):

    def setUp(self):
        create_tables()

    def test_list(self):

        stl = DatabaseCollection(type=ScheduledTicker, attribute="ticker")

        # check that append works
        stl.append("APPL")

        # check that __getitem__ works
        self.assertEqual("APPL", stl[0])

        # check that len works
        self.assertEqual(1, len(stl))

        # check that contains works
        self.assertIn("APPL", stl)

        # add another item
        stl.append("FOOBAR")
        self.assertEqual("FOOBAR", stl[1])
        self.assertEqual(2, len(stl))

        # check that __iter__ works
        for i in stl:
            self.assertNotEqual(None, i)

        # check that remove works
        stl.remove("APPL")
        self.assertEqual("FOOBAR", stl[0])
        self.assertEqual(1, len(stl))

        stl.remove("FOOBAR")
        self.assertEqual(0, len(stl))
