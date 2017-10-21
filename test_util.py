import unittest

from stockbot.util import colorify


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