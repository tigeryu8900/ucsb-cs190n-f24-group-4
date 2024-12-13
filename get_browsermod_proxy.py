"""
Download uBlock Origin .crx file
"""
from netunicorn.base import Failure, Result, Success, Task, TaskDispatcher
from netunicorn.base.architecture import Architecture
from netunicorn.base.nodes import Node


class GetBrowsermodProxy(TaskDispatcher):
    def __init__(
            self,
            *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.linux_implementation = GetBrowsermodProxyLinuxImplementation(
            name=self.name
        )

    @staticmethod
    def get() -> Result[str, str]:
        import subprocess
        from urllib import request
        from urllib.error import HTTPError

        try:
            request.urlretrieve(
                "https://github.com/lightbody/browsermob-proxy/releases/download/browsermob-proxy-2.1.4/browsermob-proxy-2.1.4-bin.zip",
                filename="/tmp/browsermob-proxy.zip"
            )
        except HTTPError:
            return Failure("Failed to download uBlock Origin")

        subprocess.run(
            ["unzip", "browsermob-proxy.zip"],
            cwd="/tmp"
        )

        return Success("Downloaded uBlock Origin")

    def dispatch(self, node: Node) -> Task:
        if node.architecture in {Architecture.LINUX_AMD64, Architecture.LINUX_ARM64}:
            return self.linux_implementation

        raise NotImplementedError(
            f'GetUblockOrigin is not implemented for architecture: {node.architecture}'
        )


class GetBrowsermodProxyLinuxImplementation(Task):
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

    def run(self):
        return GetBrowsermodProxy.get()


if __name__ == "__main__":
    print(GetBrowsermodProxy.get())
