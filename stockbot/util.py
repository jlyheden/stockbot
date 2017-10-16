def colorify(msg):

    # split over comma separated "sections"
    section_split = msg.split(",")

    rv = []

    for section in section_split:

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

                # negative gets colored red
                if v < 0:
                    value_replace = "\x0304{}\x03".format(s_split[1])

                # positive gets colored green
                else:
                    value_replace = "\x0303{}\x03".format(s_split[1])

            except ValueError as e:

                # a non-number gets colored grey
                value_replace = "\x0314{}\x03".format(s_split[1])
            finally:
                s_replace = "\x0306{k}\x03:{v}".format(k=s_split[0], v=value_replace)

        # append the result into a list
        rv.append(s_replace)

    # sew the list together into a string again
    return "\x0300,\x03".join(rv)
