import os

DEFAULT_VALUES = {
    "scheduler": "false",
    "database_url": "sqlite:///:memory:",
    "server_password": "",
    "server_use_ssl": "false",
    "die_when_not_pinged": "false",
    "die_when_not_pinged_in_s": "600",
    "game_ignore_list": ""
}


class Configuration(object):

    def __getattr__(self, item: str):
        value = os.getenv(item.upper(), self.default_wrapper(item))
        if value is None:
            raise RuntimeError("Must set environment variable {}".format(item.upper()))
        else:
            if item.endswith("_list"):
                if not value:
                    return []
                else:
                    return value.split(",")
            if value.lower() in ["true", "false"]:
                return value.lower() == "true"
            return value

    @staticmethod
    def default_wrapper(item):
        if item in DEFAULT_VALUES:
            return DEFAULT_VALUES[item]
        return None


configuration = Configuration()
