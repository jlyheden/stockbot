import unittest
from datetime import datetime
from unittest.mock import patch

from stockbot.timer import OneshotTimer


class TestOneshotTimer(unittest.TestCase):

    @patch('stockbot.timer.datetime')
    def test_should_fire(self, datetime_mock):
        fire_after = datetime.strptime("2022-12-12T16:00:00.0000Z", "%Y-%m-%dT%H:%M:%S.%f%z")
        sut = OneshotTimer("cmd", fire_after)
        unix_timestamp_after = int(fire_after.timestamp()) + sut.seconds_slack + 1
        datetime_mock.now.return_value = datetime.fromtimestamp(unix_timestamp_after)
        datetime_mock.fromtimestamp.side_effect = lambda *args, **kw: datetime.fromtimestamp(*args, **kw)
        datetime_mock.side_effect = lambda *args, **kw: datetime(*args, **kw)

        self.assertTrue(sut.should_fire())

    @patch('stockbot.timer.datetime')
    def test_should_not_fire(self, datetime_mock):
        fire_after = datetime.strptime("2022-12-12T16:00:00.0000Z", "%Y-%m-%dT%H:%M:%S.%f%z")
        sut = OneshotTimer("cmd", fire_after)
        unix_timestamp_before = int(fire_after.timestamp()) - 300
        datetime_mock.now.return_value = datetime.fromtimestamp(unix_timestamp_before)
        datetime_mock.fromtimestamp.side_effect = lambda *args, **kw: datetime.fromtimestamp(*args, **kw)
        datetime_mock.side_effect = lambda *args, **kw: datetime(*args, **kw)

        self.assertFalse(sut.should_fire())
