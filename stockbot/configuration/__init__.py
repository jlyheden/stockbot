import os

DEFAULT_VALUES = {
    "scheduler": "false",
    "database": "sqlite:///:memory:"
}


class Configuration(object):

    def __getattr__(self, item):
        value = os.getenv(item.upper(), self.default_wrapper(item))
        if value is None:
            raise RuntimeError("Must set environment variable {}".format(item.upper()))
        else:
            if value.lower() in ["true", "false"]:
                return True if value.lower() == "true" else False
            return value

    @staticmethod
    def default_wrapper(item):

        if item in DEFAULT_VALUES:
            return DEFAULT_VALUES[item]
        return None
