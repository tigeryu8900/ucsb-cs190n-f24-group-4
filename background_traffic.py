import signal
import subprocess
import time

from netunicorn.base import (
    Architecture,
    Failure,
    Node,
    Result,
    Success,
    Task,
    TaskDispatcher,
)
from netunicorn.library.tasks.tasks_utils import subprocess_run


class StartBackgroundTraffic(TaskDispatcher):
    def __init__(
            self, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.linux_implementation = StartBackgroundTrafficLinuxImplementation(
            *args, **kwargs
        )

    def dispatch(self, node: Node) -> Task:
        if node.architecture in {Architecture.LINUX_AMD64, Architecture.LINUX_ARM64}:
            return self.linux_implementation

        raise NotImplementedError(
            f"StartBackgroundTraffic is not implemented for {node.architecture}"
        )


class StartBackgroundTrafficLinuxImplementation(Task):
    requirements = ["pip install speedtest-cli"]

    def __init__(
            self, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)

    def run(self) -> Result:
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)

        proc = subprocess.Popen(
            ["sh", "-c", "while true; do speedtest-cli --simple --secure; echo asdf; done"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(2)
        if (exit_code := proc.poll()) is None:  # not finished yet
            return Success(proc.pid)

        text = ""
        if proc.stdout:
            text += proc.stdout.read().decode("utf-8") + "\n"
        if proc.stderr:
            text += proc.stderr.read().decode("utf-8")
        return Failure(f"sh terminated with return code {exit_code}" + text)


class StopNamedBackgroundTraffic(TaskDispatcher):
    def __init__(self, start_background_traffic_task_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_background_traffic_task_name = start_background_traffic_task_name
        self.linux_implementation = StopNamedBackgroundTrafficImplementation(
            background_traffic_task_name=self.start_background_traffic_task_name,
            *args,
            **kwargs,
        )

    def dispatch(self, node: Node) -> Task:
        if node.architecture in {Architecture.LINUX_AMD64, Architecture.LINUX_ARM64}:
            return self.linux_implementation

        raise NotImplementedError(
            f"StopNamedBackgroundTraffic is not implemented for {node.architecture}"
        )


class StopNamedBackgroundTrafficImplementation(Task):
    requirements = [
        "sudo apt-get update",
        "sudo apt-get install -y procps",
    ]

    def __init__(self, background_traffic_task_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.background_traffic_task_name = background_traffic_task_name

    def run(self):
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)
        pid = self.previous_steps.get(
            self.background_traffic_task_name, [Failure("Named StartBackgroundTraffic not found")]
        )[-1]
        if isinstance(pid, Failure):
            return pid

        pid = pid.unwrap()
        return subprocess_run(["kill", str(pid)])
