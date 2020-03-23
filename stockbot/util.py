import re
from colors import *


class ColorHelper(object):

    @classmethod
    def white(cls, value):
        return r"\x0300{}\x03".format(value)

    @classmethod
    def bold(cls, value):
        return r"\x02{}\x02".format(value)

    @classmethod
    def red(cls, value):
        return r"\x0304{}\x03".format(value)

    @classmethod
    def green(cls, value):
        return r"\x0303{}\x03".format(value)

    @classmethod
    def grey(cls, value):
        return r"\x0314{}\x03".format(value)

    @classmethod
    def yellow(cls, value):
        return r"\x0308{}\x03".format(value)

    @classmethod
    def purple(cls, value):
        return r"\x0306{}\x03".format(value)


def colorify(msg):

    num_change_regex = re.compile("[^\w]?total (percentage return|return)[^\w]?", flags=re.IGNORECASE)
    num_important_change_regex = re.compile("[^\w]?change[^\w]?", flags=re.IGNORECASE)
    num_recommendations_regex = re.compile("[^\w]?recommendations [^\w]?", flags=re.IGNORECASE)

    # split over pipe separated "groups"
    group_split = msg.split("|")
    group_rv = []

    for group in group_split:

        # split over comma separated "sections"
        section_split = group.split(",")

        section_rv = []

        for (index, section) in enumerate(section_split):

            # split over subject : value
            s_split = section.split(":", 1)

            # there was no subject, just color everything grey
            if len(s_split) == 1:
                s_replace = ColorHelper.grey(s_split[0])

            # we identified subject : value
            else:
                (key, value) = s_split
                try:

                    # if value is a number
                    v = float(value)

                    # truncate decimals
                    v_s = " {:.3f}".format(v)

                    # check if number should be colored differently depending on positive or negative value
                    if num_change_regex.search(key) is not None:
                        # negative gets colored red
                        if v < 0:
                            value_replace = color(v_s, fg='red')

                        # positive gets colored green
                        else:
                            value_replace = color(v_s, fg='green')
                    elif num_important_change_regex.search(key) is not None:
                        # negative gets colored red and bold
                        if v < 0:
                            value_replace = color(v_s, fg='red', style='bold')

                        # positive gets colored green and bold
                        else:
                            value_replace = color(v_s, fg='green', style='bold')
                    else:
                        # unknown number gets colored grey
                        value_replace = color(v_s, fg='grey')

                except ValueError as e:

                    # first value should be white and highlighted
                    if index == 0:
                        value_replace = color(value, fg='white', style='bold')
                    elif num_recommendations_regex.search(key) is not None:
                        # avanza recommendations in form of buy/hold/sell
                        r_split = value.split("/")
                        if len(r_split) == 3:
                            value_replace = r"{}/{}/{}".format(color(r_split[0], fg='green'),
                                                               color(r_split[1], fg='yellow'),
                                                               color(r_split[2], fg='red'))
                        else:
                            value_replace = color(value, fg='grey')
                    else:
                        # a non-number gets colored grey
                        value_replace = color(value, fg='grey')
                finally:
                    s_replace = r"{k}:{v}".format(k=color(key, fg='purple'), v=value_replace)

            # append the result into a list
            section_rv.append(s_replace)

        # sew the list together into a string again
        group_rv.append(ColorHelper.white(",").join(section_rv))
    return "|".join(group_rv)
