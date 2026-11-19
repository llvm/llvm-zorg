FROM ghcr.io/llvm/ci-ubuntu-26.04:c91364399c7c

# TODO(boomanaiden154): Temporary, we probably want to switch to sccache
RUN sudo apt-get update && sudo apt-get install -y ccache
RUN pip3 install --break-system-packages buildbot-worker==3.11.9
RUN mkdir /home/gha/app
WORKDIR /home/gha/app
COPY --chown=gha:gha startup.sh liveness.sh ./
ENTRYPOINT /home/gha/app/startup.sh
