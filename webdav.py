import os
from typing import Literal, Optional, Set

from netunicorn.base import Architecture, Failure, Node, Success, Task, TaskDispatcher
from netunicorn.library.tasks.tasks_utils import subprocess_run


class UploadToWebDav(TaskDispatcher):
    def __init__(
        self,
        filepaths: Set[str],
        endpoint: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        authentication: Literal["basic"] = "basic",
        subdirectory: Optional[str] = None,
        *args,
        **kwargs,
    ):
        if endpoint[-1] == "/":
            endpoint = endpoint[:-1]
        self.filepaths = filepaths
        self.endpoint = endpoint
        self.username = username
        self.password = password
        self.authentication = authentication
        self.subdirectory = subdirectory

        super().__init__(*args, **kwargs)

        self.linux_implementation = UploadToWebDavImplementation(
            self.filepaths,
            self.endpoint,
            self.username,
            self.password,
            self.authentication,
            self.subdirectory,
            name=self.name,
        )
        self.linux_implementation.requirements = ["sudo apt-get install -y curl"]

    def dispatch(self, node: Node) -> Task:
        if node.architecture in {Architecture.LINUX_AMD64, Architecture.LINUX_ARM64}:
            return self.linux_implementation

        raise NotImplementedError(
            f"UploadToWebDav is not implemented for {node.architecture}"
        )


class UploadToWebDavImplementation(Task):
    def __init__(
        self,
        filepaths: Set[str],
        endpoint: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        authentication: Literal["basic"] = "basic",
        subdirectory: Optional[str] = None,
        *args,
        **kwargs,
    ):
        self.filepaths = filepaths
        self.endpoint = endpoint
        self.username = username
        self.password = password
        self.authentication = authentication
        self.subdirectory = subdirectory
        super().__init__(*args, **kwargs)

    def run(self):
        results = []
        for file in self.filepaths:
            command = ["curl", "-T", file, f"{self.endpoint}/{self.subdirectory}/{file}"]
            if self.authentication == "basic":
                command += ["--user", f"{self.username}:{self.password}", "--basic"]
            results.append(subprocess_run(command))
        container_type = Success if all(isinstance(x, Success) for x in results) else Failure
        return container_type(results)
