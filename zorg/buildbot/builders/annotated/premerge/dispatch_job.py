"""Dispatches a job to the k8s cluster.

This script takes in a commit SHA to test along with the platform, spawns a job
to test it, and then streams the logs from the job. We read logs from the job
every so often using the kuberntes logging API rather than directly executing
commands inside the container and streaming the output. This is to work
around https://github.com/kubernetes-sigs/apiserver-network-proxy/issues/748.
"""

import sys
import logging
import time
import dateutil
import datetime
import json
import os

import kubernetes

PLATFORM_TO_NAMESPACE = {
    "Linux": "llvm-premerge-linux-buildbot",
    "Windows": "llvm-premerge-windows-buildbot",
}
LOG_SECONDS_TO_QUERY = 10
SECONDS_QUERY_LOGS_EVERY = 5


def start_build(k8s_client, pod_name: str, namespace: str, commands: list[str]) -> None:
    """Spawns a pod to run the specified commands.

    Args:
      k8s_client: The kubernetes client instance to use for spawning the pod.
      pod_name: The name of the pod to start.
      namespace: The namespace to launch the pod in.
      commands: The commands to run upon pod start.
    """
    pod_definition = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": pod_name,
            "namespace": namespace,
        },
        "spec": {
            "tolerations": [
                {
                    "key": "buildbot-platform",
                    "operator": "Equal",
                    "value": "linux",
                    "effect": "NoSchedule",
                }
            ],
            "nodeSelector": {"buildbot-platform": "linux"},
            "containers": [
                {
                    "name": "build",
                    "image": "ghcr.io/llvm/ci-ubuntu-24.04",
                    "command": commands,
                    "resources": {
                        "requests": {"cpu": 55, "memory": "200Gi"},
                        "limits": {"cpu": 64, "memory": "256Gi"},
                    },
                }
            ],
            "restartPolicy": "Never",
        },
    }
    kubernetes.utils.create_from_dict(k8s_client, pod_definition)


def start_build_linux(commit_sha: str, k8s_client) -> str:
    """Starts a pod to build/test on Linux at the specified SHA."""
    pod_name = f"build-{commit_sha}"
    commands = [
        "git clone --depth 100 https://github.com/llvm/llvm-project",
        "cd llvm-project",
        f"git checkout {commit_sha}",
        "export CC=clang",
        "export CXX=clang++",
        "export POSTCOMMIT_CI=1",
        './.ci/monolithic-linux.sh "polly" "check-polly" "" "" "" OFF',
        #'./.ci/monolithic-linux.sh "bolt;clang;clang-tools-extra;flang;libclc;lld;lldb;llvm;mlir;polly" "check-bolt check-clang check-clang-cir check-clang-tools check-flang check-lld check-lldb check-llvm check-mlir check-polly" "compiler-rt;libc;libcxx;libcxxabi;libunwind" "check-compiler-rt check-libc" "check-cxx check-cxxabi check-unwind" "OFF"'
        "echo BUILD FINISHED",
    ]
    start_build(
        k8s_client,
        pod_name,
        PLATFORM_TO_NAMESPACE["Linux"],
        ["/bin/bash", "-c", ";".join(commands)],
    )
    return pod_name


def start_build_windows(commit_sha: str, k8s_client):
    """Starts a pod to build/test on Windows at the specified SHA."""
    pod_name = f"build-{commit_sha}"
    bash_commands = [
        "git clone --depth 100 https://github.com/llvm/llvm-project",
        "cd llvm-project",
        f"git checkout ${commit_sha}",
        "export POSTCOMMIT_CI=1",
        '.ci/monolithic-windows.sh "clang;clang-tools-extra;libclc;lld;llvm;mlir;polly" "check-clang check-clang-cir check-clang-tools check-lld check-llvm check-mlir check-polly"',
        "echo BUILD FINISHED",
    ]
    commands = [
        "call C:\\BuildTools\\Common7\\Tools\\VsDevCmd.bat -arch=amd64 -host_arch=amd64",
        "bash",
        "-c",
        ";".join(bash_commands),
    ]
    start_build(k8s_client, pod_name, PLATFORM_TO_NAMESPACE["Windows"], commands)
    return pod_name


def read_logs(pod_name: str, namespace: str, v1_api) -> list[str]:
    """Reads logs from the specified pod.

    Reads logs using the k8s API and returns a nicely formatted list of
    strings.

    Args:
      pod_name: The name of the pod to read logs from.
      namespace: The namespace the pod is in.
      v1_api: The kubernetes API instance to use for querying logs.

    Returns:
      A list of strings representing the log lines.
    """
    logs = v1_api.read_namespaced_pod_log(
        name=pod_name,
        namespace=namespace,
        timestamps=True,
        since_seconds=LOG_SECONDS_TO_QUERY,
    )
    return logs.split("\n")[:-1]


def get_logs_to_print(
    logs: list[str], latest_time: datetime.datetime
) -> tuple[datetime.datetime, list[str]]:
    """Get the logs that we should be printing.

    This function takes in a raw list of logs along with the timestamp of the
    last log line to be printed and returns the new log lines that should be
    printed.

    Args:
      logs: The raw list of log lines.
      latest_time: The timestamp from the last log line that was printed.

    Returns:
      A tuple containing the timestamp of the last log line returned and a list
      of strings containing the log lines that should be printed.
    """
    first_new_index = 0
    time_stamp = latest_time
    for log_line in logs:
        time_stamp_str = log_line.split(" ")[0]
        time_stamp = dateutil.parser.parse(time_stamp_str[:-1])
        if time_stamp > latest_time:
            break
        first_new_index += 1
    last_time_stamp = latest_time
    if logs:
        last_time_stamp_str = logs[-1].split(" ")[0]
        last_time_stamp = dateutil.parser.parse(last_time_stamp_str[:-1])
    return (last_time_stamp, logs[first_new_index:])


def print_logs(
    pod_name: str, namespace: str, v1_api, lastest_time: datetime.datetime
) -> tuple[bool, datetime.datetime]:
    """Queries the pod and prints the relevant log lines.

    Args:
      pod_name: The pod to print the logs for.
      namespace: The namespace the log is in.
      v1_api: The kubernetes API client instance to use for querying the logs.
      latest_time: The timestamp of the last log line to be printed.

    Returns:
      A tuple containing a boolean representing whether or not the pod has
      finished executing and the timestamp of the last log line printed.
    """
    logs = read_logs(pod_name, namespace, v1_api)
    new_time_stamp, logs_to_print = get_logs_to_print(logs, lastest_time)
    pod_finished = False
    for log_line in logs_to_print:
        print(log_line.split("\r")[-1])
        if "BUILD FINISHED" in log_line:
            pod_finished = True

    return (pod_finished, new_time_stamp)


def main(commit_sha: str, platform: str):
    kubernetes.config.load_incluster_config()
    k8s_client = kubernetes.client.ApiClient()
    if platform == "Linux":
        pod_name = start_build_linux(commit_sha, k8s_client)
    elif platform == "Windows":
        pod_name = start_build_windows(commit_sha, k8s_client)
    else:
        raise ValueError("Unrecognized platform.")
    namespace = PLATFORM_TO_NAMESPACE[platform]
    latest_time = datetime.datetime.min
    v1_api = kubernetes.client.CoreV1Api()
    print("@@@BUILD_STEP Build/Test@@@")
    while True:
        try:
            pod_finished, latest_time = print_logs(
                pod_name, namespace, v1_api, latest_time
            )
            if pod_finished:
                break
        except kubernetes.client.exceptions.ApiException as log_exception:
            if "ContainerCreating" in json.loads(log_exception.body)["message"]:
                logging.warning(
                    "Cannot yet read logs from the pod: waiting for the container to start."
                )
            else:
                logging.error(f"Failed to get logs from the pod: {log_exception}")
                break
        time.sleep(SECONDS_QUERY_LOGS_EVERY)
    v1_api.delete_namespaced_pod(pod_name, namespace)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        logging.fatal("Expected usage is dispatch_job.py {platform}")
        sys.exit(1)
    if "BUILDBOT_REVISION" not in os.environ:
        logging.fatal("Expected to have BUILDBOT_REVISION environment variable set.")
        sys.exit(1)
    main(os.environ["BUILDBOT_REVISION"], sys.argv[1])
