import unittest

from stockbot.util import colorify, ColorHelper


@unittest.skip
class TestColorify(unittest.TestCase):

    def test_help_string(self):
        """validate colorify on help string"""

        s = "Usage: quote get <idx>      - returns the data for <idx>"
        cs = colorify(s)
        self.assertEqual("\x0306Usage\x03:\x02\x0300 quote get <idx>      - returns the data for <idx>\x03\x02", cs)

    def test_price_string(self):
        """validate colorify on price string"""

        # positive price
        s = "Price: 1.001"
        e = "{k}:{v}".format(k=ColorHelper.purple("Price"), v=ColorHelper.grey(" 1.001"))
        cs = colorify(s)
        self.assertEqual(e, cs)

        # negative price
        s = "Price: -1.001"
        e = "{k}:{v}".format(k=ColorHelper.purple("Price"), v=ColorHelper.grey(" -1.001"))
        cs = colorify(s)
        self.assertEqual(e, cs)

    def test_change_string(self):
        """validate colorify on price change string"""

        # positive change
        s = "Total Return Percent: 1.001"
        e = "{k}:{v}".format(k=ColorHelper.purple("Total Return Percent"),
                             v=ColorHelper.bold(ColorHelper.white(" 1.001")))
        cs = colorify(s)
        self.assertEqual(e, cs)
        #self.assertEqual("\x0306Total Return Percent\x03:\x0303 1.001\x03", cs)

        # negative change
        s = "Total Return Percent: -1.001"
        cs = colorify(s)
        self.assertEqual("\x0306Total Return Percent\x03:\x0304 -1.001\x03", cs)

    def test_important_change_string(self):
        """validate colorify on important price change string"""

        # positive change
        s = "Something Change Percent: 1.001"
        cs = colorify(s)
        self.assertEqual("\x0306Something Change Percent\x03:\x02\x0303 1.001\x03\x02", cs)

        # negative change
        s = "Something Change Percent: -1.001"
        cs = colorify(s)
        self.assertEqual("\x0306Something Change Percent\x03:\x02\x0304 -1.001\x03\x02", cs)

#    def test_multiple_groups_string(self):
#        s = "Person: X, Stats: foo | Person: Y, Stats: bar"
#        cs = colorify(s)
#        self.assertEqual("{k1g1}:{v1g1},{k2g1}:{v2g1}|{k1g2}.{v1g2},{k2g2}.{v2g2}".format(
#            k1g1=ColorHelper.purple("Person"),
#            v1g1=ColorHelper.bold(ColorHelper.white(" X")),
#            k2g1=ColorHelper.purple("Stats"),
#            v2g1=ColorHelper.grey(" foo"),
#            k1g2=ColorHelper.purple("Person"),
#            v1g2=ColorHelper.bold(ColorHelper.white(" Y")),
#            k2g2=ColorHelper.purple("Stats"),
#            v2g2=ColorHelper.grey(" bar")), cs)
