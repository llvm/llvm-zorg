FROM docker.io/python:3.13

COPY . .
RUN pip3 install --no-cache-dir -r requirements.lock.txt

CMD ["python3", "server.py"]
