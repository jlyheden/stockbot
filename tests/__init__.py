import stockbot.configuration
import tempfile
import os

tmp_dir = tempfile.TemporaryDirectory()

# cannot run in-memory db because it doesn't work well with multiple threads
stockbot.configuration.DEFAULT_VALUES["database_url"] = "sqlite:///{}".format(os.path.join(tmp_dir.name, "ircbot.db"))
