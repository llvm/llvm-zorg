FROM ubuntu:24.04
RUN apt-get update && apt-get install -y \
  python3 \
  python3-pip \
  git \
  python-is-python3
COPY requirements.lock.txt /requirements.lock.txt
RUN pip3 install --break-system-packages -r /requirements.lock.txt && rm /requirements.lock.txt
RUN mkdir /app
WORKDIR /app
COPY startup.sh .
RUN chmod +x startup.sh
ENTRYPOINT /app/startup.sh
