[![Coverage Status](https://coveralls.io/repos/github/jlyheden/stockbot/badge.svg?branch=master)](https://coveralls.io/github/jlyheden/stockbot?branch=master)

# stockbot

An IRC bot that mostly fetches stock quotes from various sources, supports simple scheduling mechanisms and
can also be interacted with using a CLI.

## Usage

### Daemon

For personal use the bot gets deployed as a Heroku worker dyno but running in docker or other platform should work
just fine. Check out the docker-compose.yml for inspiration.

### CLI

Invoke using the cli.py file:
```
$ python cli.py help
```

Some commands rely on a scheduler and others rely on database connectivity. But most get commands should work fine using
the CLI.