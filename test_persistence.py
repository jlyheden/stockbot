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
        self.assertEquals("APPL", stl[0])

        # check that len works
        self.assertEquals(1, len(stl))

        # check that contains works
        self.assertIn("APPL", stl)

        # add another item
        stl.append("FOOBAR")
        self.assertEquals("FOOBAR", stl[1])
        self.assertEquals(2, len(stl))

        # check that __iter__ works
        for i in stl:
            self.assertNotEqual(None, i)

        # check that remove works
        stl.remove("APPL")
        self.assertEquals("FOOBAR", stl[0])
        self.assertEquals(1, len(stl))

        stl.remove("FOOBAR")
        self.assertEquals(0, len(stl))
