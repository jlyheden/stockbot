import unittest
import json
import os
import datetime

from app import BloombergQuote, colorify, ScheduleHandler

CWD = os.path.dirname(os.path.realpath(__file__))


class TestBloombergQuote(unittest.TestCase):

    def test_parse_withdata(self):
        """parse bloomberg json quote"""
        with open(os.path.join(CWD, "mock", "omxs30.json"), 'r') as f:
            data = json.load(f)
        tm = BloombergQuote(message=data)

        self.assertEquals("OMX:IND", tm.id)
        self.assertEquals(8.25818928, tm.totalReturnYtd)
        self.assertEquals("OMX Stockholm 30 Index", tm.name)
        self.assertEquals("", tm.primaryExchange)
        self.assertEquals(1642.49, tm.price)
        self.assertEquals("SEK", tm.issuedCurrency)
        self.assertEquals(-5.434, tm.priceChange1Day)
        self.assertEquals(-0.329748, tm.percentChange1Day)
        self.assertEquals(3, tm.priceMinDecimals)
        self.assertEquals("03:00:00.000", tm.nyTradeStartTime)
        self.assertEquals("11:35:00.000", tm.nyTradeEndTime)
        self.assertEquals(-4, tm.timeZoneOffset)
        self.assertEquals("1507645468", tm.lastUpdateEpoch)
        self.assertEquals(1647.925, tm.openPrice)
        self.assertEquals(1642.214, tm.lowPrice)
        self.assertEquals(1651.131, tm.highPrice)
        self.assertEquals(78347792, tm.volume)
        self.assertEquals(1647.924, tm.previousClosingPriceOneTradingDayAgo)
        self.assertEquals(1391.806, tm.lowPrice52Week)
        self.assertEquals(1658.873, tm.highPrice52Week)
        self.assertEquals(15.89318, tm.totalReturn1Year)
        self.assertEquals("10/10/2017", tm.priceDate)
        self.assertEquals("10:24 AM", tm.priceTime)
        self.assertEquals("10:24 AM", tm.lastUpdateTime)
        self.assertEquals("2017-10-10T14:24:28.000Z", tm.lastUpdateISO)
        self.assertEquals("EDT", tm.userTimeZone)
        self.assertEquals("Name: OMX Stockholm 30 Index, Price: 1642.49, Open Price: 1647.925, Low Price: 1642.214, High Price: 1651.131, Percent Change 1 Day: -0.329748, Update Time: 2017-10-10 16:24:28", str(tm))

    def test_parse_nodata(self):
        """instantiate without valid quotedata"""
        tm = BloombergQuote()
        self.assertEquals("N/A", tm.name)
        self.assertEquals("Name: N/A, Price: N/A, Open Price: N/A, Low Price: N/A, High Price: N/A, Percent Change 1 Day: N/A, Update Time: N/A", str(tm))


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
