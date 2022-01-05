from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import os

downloads_path = os.path.abspath(os.path.curdir)


def start_browser():
    global browser

    options = Options()
    options.add_experimental_option("prefs", {
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False,
    })

    browser = webdriver.Chrome(options=options)
    params = {'behavior': 'allow', 'downloadPath': downloads_path}
    browser.execute_cdp_cmd('Page.setDownloadBehavior', params)
