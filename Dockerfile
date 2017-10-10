FROM python:3.6-slim

ADD requirements.txt /tmp

RUN pip install -r /tmp/requirements.txt

COPY app.py /

CMD ["/usr/bin/env", "python", "/app.py"]