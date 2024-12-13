"""
Selenium-based YouTube watcher
"""
import copy
import os
import subprocess
import time
from collections.abc import Sequence, Callable
from enum import IntEnum
from typing import Optional

from netunicorn.base import Result, Success, Task, TaskDispatcher
from netunicorn.base.architecture import Architecture
from netunicorn.base.nodes import Node


# from playwright.sync_api import sync_playwright
#
# with sync_playwright() as p:
#     for browser_type in [p.chromium, p.firefox, p.webkit]:
#         browser = browser_type.launch()
#         page = browser.new_page()
#         page.goto('http://playwright.dev')
#         page.screenshot(path=f'example-{browser_type.name}.png')
#         browser.close()

class YouTubeIFrameStatus(IntEnum):
    UNSTARTED = -1
    ENDED = 0
    PLAYING = 1
    PAUSED = 2
    BUFFERING = 3
    CUED = 5


class WatchYouTubeVideo(TaskDispatcher):
    def __init__(
            self,
            video_url: str | list[str],
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
        self.linux_implementation = WatchYouTubeVideoLinuxImplementation(
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
            urls: str | list[str],
            duration: Optional[int] = 100,
            chrome_location: Optional[str] = None,
            webdriver_arguments: Optional[list] = None,
            extensions: Optional[list[str]] = None,
            headless: Optional[bool] = True,
            processes: Optional[list[str | bytes | os.PathLike[str] | os.PathLike[bytes] | Sequence[str | bytes | os.PathLike[str] | os.PathLike[bytes]]]] = None
    ) -> Result[str, str]:
        from playwright.sync_api import sync_playwright

        procs = [] if processes is None else [subprocess.Popen(
            process,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL
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

            with sync_playwright() as p, p.chromium.launch(
                    headless=headless,
                    executable_path=chrome_location,
                    args=args,
            ) as browser:
                for url in urls:
                    with browser.new_page(
                        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                    ) as page:
                        try:
                            page.goto(url)

                            video = page.locator('#movie_player').element_handle()

                            player_status = video.evaluate('element => element?.getPlayerState()')
                            if player_status is None:
                                # return Failure("Failed to get player status")
                                pass

                            for _ in range(60):
                                try:
                                    player_status = video.evaluate('element => element?.getPlayerState()')
                                    if player_status == YouTubeIFrameStatus.PLAYING:
                                        break
                                    for button in video.query_selector_all('[id^="skip-button"]'):
                                        button.click()
                                    time.sleep(2)
                                except Exception as e:
                                    print(e)

                            if player_status != YouTubeIFrameStatus.PLAYING:
                                # return Failure("Couldn't start the video: unknown error")
                                print("Couldn't start the video: unknown error")

                            while player_status == YouTubeIFrameStatus.BUFFERING:
                                time.sleep(1)
                                player_status = video.evaluate('element => element?.getPlayerState()')

                            if player_status in {
                                YouTubeIFrameStatus.UNSTARTED,
                                YouTubeIFrameStatus.CUED,
                                YouTubeIFrameStatus.PAUSED,
                            }:
                                video.type(" ")
                                time.sleep(2)

                                for _ in range(60):
                                    try:
                                        player_status = video.evaluate('element => element?.getPlayerState()')
                                        if player_status == YouTubeIFrameStatus.PLAYING:
                                            break
                                        for button in video.query_selector_all('[id^="skip-button"]'):
                                            button.click()
                                        time.sleep(2)
                                    except Exception as e:
                                        print(e)

                                if player_status != YouTubeIFrameStatus.PLAYING:
                                    # return Failure("Couldn't start the video: unknown error")
                                    print("Couldn't start the video: unknown error")

                            if duration:
                                time.sleep(duration)
                                result = Success(f"Video finished by timeout: {duration} seconds")
                            else:
                                while player_status != YouTubeIFrameStatus.ENDED:
                                    while player_status != YouTubeIFrameStatus.PLAYING:
                                        player_status = video.evaluate('element => element?.getPlayerState()')
                                        for button in video.query_selector_all('[id^="skip-button:2"]'):
                                            button.click()
                                        time.sleep(2)
                                    time.sleep(2)
                                    player_status = video.evaluate('element => element?.getPlayerState()')
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
        # from selenium.webdriver.common.by import By
        # from selenium.webdriver.common.keys import Keys
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
        #
        # if not isinstance(urls, list):
        #     urls = [urls]
        #
        # result = Success("No videos.")
        #
        # driver.get("https://www.example.com")
        #
        # for url in urls:
        #     driver.get(url)
        #
        #     video = driver.find_element(By.ID, "movie_player")
        #
        #     player_status = driver.execute_script(
        #         "return document.getElementById('movie_player').getPlayerState()"
        #     )
        #     if player_status is None:
        #         driver.close()
        #         xvfb_process.kill()
        #         return Failure("Failed to get player status")
        #
        #     while player_status == YouTubeIFrameStatus.BUFFERING:
        #         time.sleep(1)
        #         player_status = driver.execute_script(
        #             "return document.getElementById('movie_player').getPlayerState()"
        #         )
        #
        #     if player_status in {
        #         YouTubeIFrameStatus.UNSTARTED,
        #         YouTubeIFrameStatus.CUED,
        #         YouTubeIFrameStatus.PAUSED,
        #     }:
        #         video.send_keys(Keys.SPACE)
        #         time.sleep(2)
        #         player_status = driver.execute_script(
        #             "return document.getElementById('movie_player').getPlayerState()"
        #         )
        #         if player_status != YouTubeIFrameStatus.PLAYING:
        #             driver.close()
        #             xvfb_process.kill()
        #             return Failure("Couldn't start the video: unknown error")
        #
        #     if duration:
        #         time.sleep(duration)
        #         result = Success(f"Video finished by timeout: {duration} seconds")
        #     else:
        #         while player_status in {
        #             YouTubeIFrameStatus.PLAYING,
        #             YouTubeIFrameStatus.BUFFERING,
        #         }:
        #             time.sleep(2)
        #             player_status = driver.execute_script(
        #                 "return document.getElementById('movie_player').getPlayerState()"
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
            f'WatchYouTubeVideo is not implemented for architecture: {node.architecture}'
        )


class WatchYouTubeVideoLinuxImplementation(Task):
    requirements = [
        "apt install -y python3-pip wget xvfb procps",
        "pip3 install pytest-playwright",
        "playwright install-deps",
        "playwright install chromium"
    ]

    def __init__(
            self,
            video_url: str | list[str],
            duration: Optional[int] = None,
            chrome_location: Optional[str] = None,
            webdriver_arguments: Optional[list] = None,
            extensions: Optional[list[str]] = None,
            headless: Optional[bool] = True,
            get_processes: Optional[Callable[[str], list[str | bytes | os.PathLike[str] | os.PathLike[bytes] | Sequence[
                str | bytes | os.PathLike[str] | os.PathLike[bytes]]]]] = None,
            *args,
            **kwargs,
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
        return WatchYouTubeVideo.watch(
            self.video_url,
            self.duration,
            self.chrome_location,
            self.webdriver_arguments,
            self.extensions,
            self.headless,
            None if self.get_processes is None else self.get_processes(self.name)
        )


if __name__ == "__main__":
    print(WatchYouTubeVideo.watch([f"https://www.youtube.com/watch?v={v}" for v in [
        "dQw4w9WgXcQ",
        "r5JYHXtt_rw",
        # "pxEV1A5mTYM",
        # "Ct6BUPvE2sM",
        # "KjtYZpqvt50"
    ]], 10, headless=False))
