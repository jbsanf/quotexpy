import re
import json
import shutil
import sys
import time
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Tuple, Any
from quotexpy.exceptions import QuotexAuthError
from quotexpy.utils.playwright_install import install
from playwright.async_api import Playwright, async_playwright

import tagui
import rpa as r
import PyChromeDevTools


class Browser(object):
    email = None
    password = None

    base_url = "qxbroker.com"
    https_base_url = f"https://{base_url}"

    def __init__(self, api):
        self.api = api
    
    def __location_tagui(self) -> None:
        if sys.platform == 'win32':
            location_tagui = Path.cwd().joinpath('.tagui_win')
        else:
            location_tagui = Path.cwd().joinpath('.tagui_unix')

        r.tagui_location(location=str(location_tagui))
        if not location_tagui.exists():
            location_tagui.mkdir()
            tagui.setup()
            for file_name in ['tagui.cmd', 'tagui']:
                tagui_cfg = location_tagui.joinpath('tagui', 'src', file_name)
                with tagui_cfg.open() as f:
                    newText=f.read().replace(
                        '--remote-debugging-port=9222 about:blank',
                        '--remote-debugging-port=9222 --remote-allow-origins=* --incognito about:blank',
                    )

                with tagui_cfg.open("w") as f:
                    f.write(newText)
    
    async def run(self, playwright: Playwright) -> Tuple[Any, str]:
        self.__location_tagui()
        r.init()
        chrome_devt = PyChromeDevTools.ChromeInterface()
        r.url('https://qxbroker.com/pt/sign-in')
        r.wait()

        if r.dom('return document.URL') == 'https://qxbroker.com/pt/trade':
            source = r.dom('return document.documentElement.innerHTML')
            user_agent = r.dom('return navigator.userAgent')
        else:
            r.click('//html/body/bdi/div[1]/div/div[2]/div[3]/form/div[1]/input')
            r.type('//html/body/bdi/div[1]/div/div[2]/div[3]/form/div[1]/input', 'batista.santos@ymail.com')

            r.click('//html/body/bdi/div[1]/div/div[2]/div[3]/form/div[2]/input')
            r.type('//html/body/bdi/div[1]/div/div[2]/div[3]/form/div[2]/input', ':kNjsU^~9}!udq?')

            r.click('//html/body/bdi/div[1]/div/div[2]/div[3]/form/button')

            if r.click('//html/body/div[2]/main/form/div[1]/label'):
                r.type('//html/body/div[2]/main/form/div[1]/label', input('Digite o código de 6 dígitos:'))
                r.click('//html/body/div[2]/main/form/div[2]/button')
                r.wait()
            
            source = r.dom('return document.documentElement.innerHTML')
            user_agent = r.dom('return navigator.userAgent')

            time.sleep(1)
        
        cookies, _ = chrome_devt.Network.getCookies()
        cookies = cookies["result"]["cookies"]
        r.close()
        self.api.cookies = cookies
        soup = BeautifulSoup(source, "html.parser")
        self.api.user_agent = user_agent
        script = soup.find_all("script", {"type": "text/javascript"})[1].get_text()
        match = re.sub("window.settings = ", "", script.strip().replace(";", ""))

        ssid = json.loads(match).get("token")
        output_file = Path(".session.json")
        output_file.parent.mkdir(exist_ok=True, parents=True)
        cookiejar = requests.utils.cookiejar_from_dict({c["name"]: c["value"] for c in cookies})
        cookie_string = "; ".join([f"{c.name}={c.value}" for c in cookiejar])

        return ssid, cookie_string

    async def get_cookies_and_ssid(self) -> Tuple[Any, str]:
        async with async_playwright() as playwright:
            browser = playwright.firefox
            if not shutil.which(browser.name):
                install(browser, with_deps=True)
            return await self.run(playwright)
