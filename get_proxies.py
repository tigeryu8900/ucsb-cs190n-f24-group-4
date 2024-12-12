import re

from bs4 import BeautifulSoup
from urllib import request


class ProxyEntry:
    def __init__(self,
                 ip: str,
                 port: int,
                 code: str,
                 country: str,
                 anonymity: str,
                 google: bool,
                 https: bool,
                 last_checked: int
):
        self.ip = ip
        self.port = port
        self.code = code
        self.country = country
        self.anonymity = anonymity
        self.google = google
        self.https = https
        self.last_checked = last_checked


def parse_last_checked(last_checked: str) -> int:
    result = 0
    for num, unit in re.findall(r'\b(\d+)\s+(hour|min|sec)s?\b', last_checked):
        num = int(num)
        match unit:
            case 'hour':
                result += num * 60 * 60
            case 'min':
                result += num * 60
            case 'sec':
                result += num
    return result


def get_proxies():
    result: list[ProxyEntry] = []
    with request.urlopen(request.Request('https://free-proxy-list.net/', headers={
        'accept': 'text/html',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    })) as response:
        response_body = response.read().decode('utf-8')
        soup = BeautifulSoup(response_body, 'html.parser')
        entries = soup.select('table tbody tr')
        for entry in entries:
            fields = entry.select('td')
            if len(fields) >= 8:
                result.append(ProxyEntry(
                    ip=fields[0].text,
                    port=int(fields[1].text),
                    code=fields[2].text,
                    country=fields[3].text,
                    anonymity=fields[4].text,
                    google=fields[5].text == 'yes',
                    https=fields[6].text == 'yes',
                    last_checked=parse_last_checked(fields[7].text)
                ))
    return result


if __name__ == '__main__':
    print(get_proxies())
