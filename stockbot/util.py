import re


def colorify(msg):

    numerical_regex = re.compile("[^\w](change|total return)[^\w]", flags=re.IGNORECASE)

    # split over comma separated "sections"
    section_split = msg.split(",")

    rv = []

    for (index, section) in enumerate(section_split):

        # split over subject : value
        s_split = section.split(":", 1)

        # there was no subject, just color everything grey
        if len(s_split) == 1:
            s_replace = "\x0314{}\x03".format(s_split[0])

        # we identified subject : value
        else:
            try:

                # if value is a number
                v = float(s_split[1])

                # check if number should be colored differently depending on positive or negative value
                if numerical_regex.search(s_split[0]) is not None:
                    # negative gets colored red
                    if v < 0:
                        value_replace = "\x0304{}\x03".format(s_split[1])

                    # positive gets colored green
                    else:
                        value_replace = "\x0303{}\x03".format(s_split[1])
                else:
                    # unknown number gets colored grey
                    value_replace = "\x0314{}\x03".format(s_split[1])
                    #value_replace = "\x0300{}\x03".format(s_split[1])

            except ValueError as e:

                # first value should be white and highlighted
                if index == 0:
                    value_replace = "\x02\x0300{}\x03\x02".format(s_split[1])
                else:
                    # a non-number gets colored grey
                    value_replace = "\x0314{}\x03".format(s_split[1])
            finally:
                s_replace = "\x0306{k}\x03:{v}".format(k=s_split[0], v=value_replace)

        # append the result into a list
        rv.append(s_replace)

    # sew the list together into a string again
    return "\x0300,\x03".join(rv)
