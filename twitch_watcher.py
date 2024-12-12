"""
Selenium-based Twitch watcher
"""
import copy
import os
import random
import subprocess
import time
from collections.abc import Callable, Sequence
from typing import Optional, Union

from netunicorn.base import Result, Success, Task, TaskDispatcher
from netunicorn.base.architecture import Architecture
from netunicorn.base.nodes import Node


class WatchTwitchStream(TaskDispatcher):
    def __init__(
        self,
        video_url: Union[str, list[str]],
        duration: Optional[int] = None,
        chrome_location: Optional[str] = None,
        webdriver_arguments: Optional[list] = None,
        extensions: Optional[list[str]] = None,
        headless: Optional[bool] = True,
        get_processes: Optional[Callable[[str], list[str | bytes | os.PathLike[str] | os.PathLike[bytes] | Sequence[
            str | bytes | os.PathLike[str] | os.PathLike[bytes]]]]] = None,
        requirements: Optional[list[str]] = None,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.video_url = video_url
        self.duration = duration
        self.chrome_location = chrome_location
        self.webdriver_arguments = webdriver_arguments
        self.extensions = extensions
        self.headless = headless
        self.get_processes = get_processes
        self.requirements = requirements
        self.linux_implementation = WatchTwitchStreamLinuxImplementation(
            self.video_url,
            self.duration,
            self.chrome_location,
            self.webdriver_arguments,
            self.extensions,
            self.headless,
            self.get_processes,
            name=self.name
        )
        if self.requirements is not None:
            self.linux_implementation.requirements = copy.deepcopy(self.linux_implementation.requirements)
            self.linux_implementation.requirements.extend(requirements)

    @staticmethod
    def watch(
            urls: Union[str, list[str]],
            duration: int = 10,
            chrome_location: Optional[str] = None,
            webdriver_arguments: Optional[list] = None,
            extensions: Optional[list[str]] = None,
            headless: Optional[bool] = True,
            processes: Optional[list[subprocess.Popen]] = None,
    ) -> Result[str, str]:
        from playwright.sync_api import sync_playwright

        procs = [] if processes is None else [subprocess.Popen(
            process,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE
        ) for process in processes]

        try:
            args = [
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-setuid-sandbox",
                "--no-sandbox",
                "--autoplay-policy=no-user-gesture-required",
                "--disable-dev-shm-usage",
            ]

            if webdriver_arguments is not None:
                args.extend(webdriver_arguments)

            if extensions is not None:
                extension_str = ','.join([
                    os.path.abspath(os.path.expanduser(extension)) for extension in extensions
                ])
                args.append(f"--disable-extensions-except={extension_str}")
                args.append(f"--load-extension={extension_str}")

            if not isinstance(urls, list):
                urls = [urls]

            with sync_playwright() as p, p.chromium.launch(
                headless=headless,
                executable_path=chrome_location,
                args=args,
            ) as browser, browser.new_page(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ) as page:
                for url in urls:
                    page.goto(url)

                    # can't find a way to check whether video is playing now, so let's just wait a timeout
                    time.sleep(duration)

            return Success(f"Video probably finished by timeout: {duration} seconds")

        finally:
            for process in procs:
                process.terminate()

        # from selenium import webdriver
        # from selenium.webdriver.chrome.options import Options
        # from selenium.webdriver.chrome.service import Service
        #
        # display_number = random.randint(100, 500)
        # xvfb_process = subprocess.Popen(
        #     ["Xvfb", f":{display_number}", "-screen", "0", "1920x1080x24"]
        # )
        # os.environ["DISPLAY"] = f":{display_number}"
        #
        # options = Options()
        # options.add_argument("--disable-background-timer-throttling")
        # options.add_argument("--disable-backgrounding-occluded-windows")
        # options.add_argument("--disable-renderer-backgrounding")
        # options.add_argument("--disable-setuid-sandbox")
        # options.add_argument("--no-sandbox")
        # options.add_argument("--autoplay-policy=no-user-gesture-required")
        # options.add_argument("--disable-dev-shm-usage")
        # if webdriver_arguments:
        #     for argument in webdriver_arguments:
        #         options.add_argument(argument)
        # if chrome_location:
        #     options.binary_location = chrome_location
        # if extensions:
        #     for extension in extensions:
        #         options.add_extension(extension)
        # driver = webdriver.Chrome(service=Service(), options=options)
        # if not isinstance(urls, list):
        #     urls = [urls]
        #
        # for url in urls:
        #     driver.get(url)
        #
        #     # can't find a way to check whether video is playing now, so let's just wait a timeout
        #     time.sleep(duration)
        #
        # result = Success(f"Video probably finished by timeout: {duration} seconds")
        # driver.close()
        # xvfb_process.kill()
        # return result

    def dispatch(self, node: Node) -> Task:
        if node.architecture in {Architecture.LINUX_AMD64, Architecture.LINUX_ARM64}:
            return self.linux_implementation

        raise NotImplementedError(
            f'WatchTwitchVideo is not implemented for architecture: {node.architecture}'
        )


class WatchTwitchStreamLinuxImplementation(Task):
    requirements = [
        "apt install -y python3-pip wget xvfb procps",
        "pip3 install pytest-playwright",
        "playwright install-deps",
        "playwright install chromium"
    ]

    def __init__(
            self,
            video_url: Union[str, list[str]],
            duration: int = 10,
            chrome_location: Optional[str] = None,
            webdriver_arguments: Optional[list] = None,
            extensions: Optional[list[str]] = None,
            headless: Optional[bool] = True,
            get_processes: Optional[Callable[[str], list[str | bytes | os.PathLike[str] | os.PathLike[bytes] | Sequence[
                str | bytes | os.PathLike[str] | os.PathLike[bytes]]]]] = None,
            *args, **kwargs
    ):
        self.video_url = video_url
        self.duration = duration
        self.chrome_location = chrome_location
        # if not self.chrome_location:
        #     self.chrome_location = "/usr/bin/chromium"
        self.webdriver_arguments = webdriver_arguments
        self.extensions = extensions
        self.headless = headless
        self.get_processes = get_processes
        super().__init__(*args, **kwargs)

    def run(self):
        return WatchTwitchStream.watch(
            self.video_url,
            self.duration,
            self.chrome_location,
            self.webdriver_arguments,
            self.extensions,
            self.headless,
            None if self.get_processes is None else self.get_processes(self.name)
        )


if __name__ == "__main__":
    print(WatchTwitchStream.watch([f"https://twitch.tv/video/{v}" for v in [
        2322690366,
        2298318732,
        2316652767,
        1867242354,
        2320975412
    ]], 30, headless=True))
