[![Build Status](https://travis-ci.org/jlyheden/stockbot.svg?branch=master)](https://travis-ci.org/jlyheden/stockbot)
[![Coverage Status](https://coveralls.io/repos/github/jlyheden/stockbot/badge.svg?branch=master)](https://coveralls.io/github/jlyheden/stockbot?branch=master)

# stockbot

A stupid simple IRC bot that returns stock quotes scheduled and on demand

## Usage

The container will throw a stack trace if you are missing some configuration, here's what's needed at some point in time:

```
$ docker run --rm \
    -e SERVER_NAME=<irc.server.fqdn> \
    -e SERVER_PORT=<irc.server.port> \
    -e CHANNEL_NAME=#<channel.to.join> \
    -e NICK=<irc.nick> \
    -e DEFAULT_TICKER=<bloomberg.stock.ticker>
    jlyheden/stockbot:latest
```

Log level can be controlled by setting the env var LOGLEVEL and maps to the built-in python logging levels name wise.

Setting env var TZ is usually a good thing unless you are living in UTC.
