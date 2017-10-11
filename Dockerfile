FROM python:3.6-slim

ADD requirements.txt /tmp

RUN pip install -r /tmp/requirements.txt && useradd -M botuser

COPY app.py /

USER botuser

CMD ["/usr/bin/env", "python", "/app.py"]