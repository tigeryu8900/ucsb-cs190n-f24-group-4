"""
Selenium-based Vimeo watcher
"""
import copy
import os
import subprocess
import time
from collections.abc import Callable, Sequence
from typing import Optional, Union

from netunicorn.base import Result, Success, Task, TaskDispatcher
from netunicorn.base.architecture import Architecture
from netunicorn.base.nodes import Node


class WatchVimeoVideo(TaskDispatcher):
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
        self.linux_implementation = WatchVimeoVideoLinuxImplementation(
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
        duration: Optional[int] = 100,
        chrome_location: Optional[str] = None,
        webdriver_arguments: Optional[list] = None,
        extensions: Optional[list[str]] = None,
        headless: bool = True,
        processes: Optional[list[subprocess.Popen]] = None
    ) -> Result[str, str]:
        from playwright.async_api import async_playwright

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

            result = Success("No videos.")

            with async_playwright() as p, p.chromium.launch(
                headless=headless,
                executable_path=chrome_location,
                args=args,
            ) as browser:
                for url in urls:
                    with browser.new_page(
                        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                    ) as page:
                        page.goto(url)

                        try:
                            paused = page.locator('video').first.evaluate('element => element.paused')
                            if paused is None:
                                # return Failure("Failed to get video status")
                                print("Failed to get video status")

                            for _ in range(5):
                                try:
                                    page.locator('video').first.evaluate('''function (element) {
                                        const isPlaying = element.currentTime > 0 && !element.paused && !element.ended 
                                            && element.readyState > element.HAVE_CURRENT_DATA;
                
                                        if (!isPlaying) {
                                          element.play();
                                        }
                                    }''')
                                    time.sleep(2)
                                    paused = page.locator('video').first.evaluate('element => element.paused')
                                    time.sleep(2)
                                    if not paused:
                                        break
                                except Exception as e:
                                    print(e)

                            if paused:
                                # return Failure("Couldn't start the video: unknown error")
                                print("Couldn't start the video: unknown error")

                            if duration:
                                time.sleep(duration)
                                result = Success(f"Video finished by timeout: {duration} seconds")
                            else:
                                paused = page.locator('video').first.evaluate('element => element.paused')
                                while not paused:
                                    time.sleep(2)
                                    paused = page.locator('video').first.evaluate('element => element.paused')
                                result = Success("Video finished by reaching the end")

                        except Exception as e:
                            print(e)

            return result

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
        # result = Success("No videos")
        #
        # for url in urls:
        #     driver.get(url)
        #
        #     paused = driver.execute_script(
        #         "return document.getElementsByTagName('video')[0]?.paused"
        #     )
        #     if paused is None:
        #         driver.close()
        #         xvfb_process.kill()
        #         return Failure("Failed to get video status")
        #
        #     for _ in range(5):
        #         driver.execute_script("document.getElementsByTagName('video')[0]?.play()")
        #         time.sleep(2)
        #         paused = driver.execute_script(
        #             "return document.getElementsByTagName('video')[0]?.paused"
        #         )
        #         time.sleep(2)
        #         if not paused:
        #             break
        #
        #     if paused:
        #         driver.close()
        #         xvfb_process.kill()
        #         return Failure("Couldn't start the video: unknown error")
        #
        #     if duration:
        #         time.sleep(duration)
        #         result = Success(f"Video finished by timeout: {duration} seconds")
        #     else:
        #         paused = driver.execute_script(
        #             "return document.getElementsByTagName('video')[0].paused"
        #         )
        #         while not paused:
        #             time.sleep(2)
        #             paused = driver.execute_script(
        #                 "return document.getElementsByTagName('video')[0].paused"
        #             )
        #         result = Success("Video finished by reaching the end")
        #
        # driver.close()
        # xvfb_process.kill()
        # return result

    def dispatch(self, node: Node) -> Task:
        if node.architecture in {Architecture.LINUX_AMD64, Architecture.LINUX_ARM64}:
            return self.linux_implementation

        raise NotImplementedError(
            f'WatchVimeoVideo is not implemented for architecture: {node.architecture}'
        )


class WatchVimeoVideoLinuxImplementation(Task):
    requirements = [
        "apt install -y python3-pip wget xvfb procps",
        "pip3 install pytest-playwright",
        "playwright install-deps",
        "playwright install chromium"
    ]

    def __init__(
        self,
        video_url: str,
        duration: Optional[int] = None,
        chrome_location: Optional[str] = None,
        webdriver_arguments: Optional[list] = None,
        extensions: Optional[list[str]] = None,
        headless: Optional[bool] = True,
        get_processes: Optional[Callable[[str], list[str | bytes | os.PathLike[str] | os.PathLike[bytes] | Sequence[
            str | bytes | os.PathLike[str] | os.PathLike[bytes]]]]] = None,
        *args,
        **kwargs
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
        return WatchVimeoVideo.watch(
            self.video_url,
            self.duration,
            self.chrome_location,
            self.webdriver_arguments,
            self.extensions,
            self.headless,
            None if self.get_processes is None else self.get_processes(self.name)
        )


if __name__ == "__main__":
    print(WatchVimeoVideo.watch([f"https://vimeo.com/{v}?autoplay=1" for v in [
        375468729,
        347119375,
        297124334,
        476306167,
        515893651
    ]], 30, headless=True))
