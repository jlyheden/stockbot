#!/usr/bin/env bash

useradd -M botuser
chown -R botuser /persistence

export -a

su - botuser -p -c "/usr/bin/env python /app.py"