"""
Download uBlock Origin .crx file
"""
from netunicorn.base import Failure, Result, Success, Task, TaskDispatcher
from netunicorn.base.architecture import Architecture
from netunicorn.base.nodes import Node


class GetAdblockPlus(TaskDispatcher):
    def __init__(
            self,
            filename: str = "/tmp/adblock-plus.crx",
            *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.filename = filename
        self.linux_implementation = GetAdblockPlusLinuxImplementation(
            self.filename,
            name=self.name
        )

    @staticmethod
    def get(
        filename: str = "/tmp/adblock-plus.crx"
    ) -> Result[str, str]:
        from urllib import request
        from urllib.error import HTTPError

        try:
            request.urlretrieve("https://files.catbox.moe/e81mwm.crx", filename=filename)
        except HTTPError:
            return Failure("Failed to download Adblock Plus")

        return Success("Downloaded Adblock Plus")

    def dispatch(self, node: Node) -> Task:
        if node.architecture in {Architecture.LINUX_AMD64, Architecture.LINUX_ARM64}:
            return self.linux_implementation

        raise NotImplementedError(
            f'GetUblockOrigin is not implemented for architecture: {node.architecture}'
        )


class GetAdblockPlusLinuxImplementation(Task):
    def __init__(
        self,
        filename: str = "/tmp/adblock-plus.crx",
        *args,
        **kwargs,
    ):
        self.filename = filename
        super().__init__(*args, **kwargs)

    def run(self):
        return GetAdblockPlus.get(filename=self.filename)


if __name__ == "__main__":
    print(GetAdblockPlus.get(filename="/tmp/adblock-plus.crx"))
