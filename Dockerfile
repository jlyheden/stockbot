FROM python:3.9-slim

RUN apt-get update && apt-get --no-install-recommends install -y git build-essential

ADD requirements.txt /tmp

RUN pip install -r /tmp/requirements.txt

COPY cmd.sh /
COPY app.py /
COPY /stockbot /stockbot

VOLUME ["/persistence"]

ARG COMMIT_HASH
ENV COMMIT_HASH=$COMMIT_HASH

CMD ["/usr/bin/env", "python", "app.py"]
