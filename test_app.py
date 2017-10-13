import unittest
import datetime

from app import colorify, ScheduleHandler


class TestColorify(unittest.TestCase):

    def test_help_string(self):
        """validate colorify on help string"""

        s = "Usage: quote get <idx>      - returns the data for <idx>"
        cs = colorify(s)
        self.assertEquals("\x0306Usage\x03:\x0314 quote get <idx>      - returns the data for <idx>\x03", cs)

    def test_price_string(self):
        """validate colorify on price string"""

        # positive price
        s = "Price: 1.001"
        cs = colorify(s)
        self.assertEquals("\x0306Price\x03:\x0303 1.001\x03", cs)

        # negative price
        s = "Price: -1.001"
        cs = colorify(s)
        self.assertEquals("\x0306Price\x03:\x0304 -1.001\x03", cs)


class TestScheduleHandler(unittest.TestCase):

    def test_timer(self):

        class PartialIrcBot(ScheduleHandler):
            pass

        t = PartialIrcBot()
        df = "%d/%m/%Y %H:%M:%S"

        for d in [9, 10, 11, 12, 13]:
            d_str = "{}/10/2017".format(d)
            for h in range(24):
                h_str = "{}:00:00".format(str(h).zfill(2))
                dt = datetime.datetime.strptime("{d} {h}".format(d=d_str, h=h_str), df)
                if h < 9 or h >= 18:
                    self.assertFalse(t.timer_should_execute(dt))
                else:
                    self.assertTrue(t.timer_should_execute(dt))

        for d in [14, 15]:
            d_str = "{}/10/2017".format(d)
            for h in range(24):
                h_str = "{}:00:00".format(str(h).zfill(2))
                dt = datetime.datetime.strptime("{d} {h}".format(d=d_str, h=h_str), df)
                self.assertFalse(t.timer_should_execute(dt))
