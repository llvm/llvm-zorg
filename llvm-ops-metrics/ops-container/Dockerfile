FROM docker.io/python:3.12

COPY requirements.lock.txt ./
RUN pip3 install --no-cache-dir -r requirements.lock.txt
COPY process_llvm_commits.py ./

CMD ["python3", "process_llvm_commits.py"]
