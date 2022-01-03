from languages import Language
import languages

import moss
import secret

import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

from dataclasses import dataclass

import glob
import logging
import os
import re
import shutil

ejudge_downloads_path = "ejudge_downloads"
ejudge_url = "https://ejudge.lksh.ru"


def run_id_from_submit_name(run):
    return int(run.lstrip('0'))


def extract_SID(url):
    return url.split("=")[1].split("&")[0]


def extract_run_id(url):
    i = url.find("run_id=")
    if i == -1:
        return ""

    return int(url[i + 7:])


def login_to_ejudge(browser):
    serve_control_url = f"{ejudge_url}/cgi-bin/serve-control"

    browser.get(serve_control_url)

    login = browser.find_element(By.NAME, "login")
    password = browser.find_element(By.NAME, "password")
    submit = browser.find_element(By.NAME, "submit")

    login.send_keys(secret.login)
    password.send_keys(secret.password)

    submit.click()


def go_to_judges(browser, contest_id):
    sid = extract_SID(browser.current_url)
    contest_judge_url = f"{ejudge_url}/cgi-bin/new-judge?SID={sid}&action=3&contest_id={contest_id}"
    browser.get(contest_judge_url)


def filter_oks_only_earliest_to_latest(browser, prob_name, not_earlier_than):
    sid = extract_SID(browser.current_url)
    judge_url = f"{ejudge_url}/cgi-bin/new-judge?SID={sid}&filter_expr=(status%3D%3DOK+||+status+%3D%3D+PR)+%26%26+latest+%26%26+id+>+{not_earlier_than}+%26%26+prob%3D%3D\"{prob_name}\"&filter_first_run=0&filter_last_run=-1"
    browser.get(judge_url)


def load_earliest_ok_page(browser):
    ok_id_xpath = "/html/body/div[@id='main-cont']/div[@id='container']/table[@class='b1'][1]/tbody/tr[2]/td[@class='b1'][1]"
    ok_id = int(browser.find_element(By.XPATH, ok_id_xpath).text)

    username_xpath = "/html/body/div[@id='main-cont']/div[@id='container']/table[@class='b1'][1]/tbody/tr[2]/td[@class='b1'][3]"
    username = browser.find_element(By.XPATH, username_xpath).text

    ok_link_xpath = "/html/body/div[@id='main-cont']/div[@id='container']/table[@class='b1'][1]/tbody/tr[2]/td[@class='b1'][8]/a"
    ok_link = browser.find_element(By.XPATH, ok_link_xpath)
    ok_link.click()

    return ok_id, username


def parse_language(text_arg):
    text = text_arg.lower()

    if text.find("c++") != -1:
        return Language.CPP
    elif text.find("python") != -1:
        return Language.PYTHON
    else:
        raise ValueError(f"Unexpected language: {text_arg}")


def load_earliest_ok(browser, contest_id, prob_name, later_than=None):
    if later_than is None:
        later_than = 0

    login_to_ejudge(browser)

    go_to_judges(browser, contest_id)

    filter_oks_only_earliest_to_latest(browser, prob_name, later_than)

    earliest_ok_id, username = load_earliest_ok_page(browser)

    lang_xpath = "/html/body/div[@id='main-cont']/div[@id='container']/div[@id='info-brief']/div[@class='table-scroll']/table[@class='table']/tbody/tr[2]/td[8]/a"
    lang = parse_language(browser.find_element(By.XPATH, lang_xpath).text)

    download_button_xpath = "/html/body/div[@id='main-cont']/div[@id='container']/div[@id='info-brief']/div[@id='brief-actions']/p/a[2]"
    download_button = browser.find_element(By.XPATH, download_button_xpath)
    download_button.click()

    return earliest_ok_id, username, lang


def download_all_oks(contest_id, prob_name, later_than=0):
    try:
        os.mkdir("ejudge_downloads")
    except FileExistsError:
        pass

    options = Options()
    options.add_experimental_option("prefs", {
        "download.default_directory": r"/home/rationalex/lksh/plague-check",
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False,
    })
    browser = webdriver.Chrome(options=options)
    params = {'behavior': 'allow', 'downloadPath': r"/home/rationalex/lksh/plague-check"}
    browser.execute_cdp_cmd('Page.setDownloadBehavior', params)

    topic = contest_topic(contest_id)

    ok_id = later_than
    ok_count = 0
    while True:
        try:
            ok_id, username, lang = load_earliest_ok(browser=browser,
                                                     contest_id=contest_id,
                                                     prob_name=prob_name,
                                                     later_than=ok_id)

            ok_filename = f"{str(ok_id).rjust(6, '0')}{languages.file_extension(lang)}"

            while not os.path.exists(ok_filename):
                pass

            logging.info(f"Downloaded {topic}-{prob_name}-{ok_id}")
            ok_count += 1

            shutil.move(ok_filename,
                        "ejudge_downloads/{}_{}_{}_{}".format(topic.replace(' ', '-'),
                                                              prob_name,
                                                              username.replace(' ', '-'),
                                                              ok_filename))

        except selenium.common.exceptions.NoSuchElementException:
            break
        except Exception as e:
            logging.info(e)
            break

    return ok_count


def contest_topic(contest_id):
    browser = webdriver.Chrome()
    login_to_ejudge(browser)
    go_to_judges(browser, contest_id)

    head_xpath = "/html/body/div[@id='main-cont']/div[@id='container']/div[@id='header']/h1"
    admin_info = re.search("\[(.+?)\]", browser.find_element(By.XPATH, head_xpath).text).group(1)
    contest_name = admin_info.split(',')[2]

    return contest_name.split('.')[-1]


@dataclass
class EjudgeSubmit:
    contest_name: str
    prob_name: str
    username: str
    run_id: int
    filepath: str
    language: Language

    @staticmethod
    def load(path):
        filename = path.split('/')[-1]
        contest_name, prob_name, username, run_filename = filename.split('_')

        for lang in languages.supported_languages:
            extension_idx = run_filename.find(languages.file_extension(lang))
            if extension_idx != -1:
                run_id = int(run_filename[:extension_idx])
                submit_lang = lang
                break
        else:
            raise ValueError(f"Language of submit {run_filename} is not supported")

        return EjudgeSubmit(contest_name=contest_name,
                            prob_name=prob_name,
                            username=username,
                            run_id=run_id,
                            language=submit_lang,
                            filepath=path)


def count_oks_downloaded(contest_id, prob_name, lang_extension):
    return len(glob.glob(f"ejudge_downloads/{contest_topic(contest_id).replace(' ', '_')}_{prob_name}_*{lang_extension}"))


def ejudge_prob_prefix(contest_id, prob_name):
    return f"{contest_topic(contest_id).replace(' ', '-')}_{prob_name}"


def last_ok_on_disk_run_id(contest_id, prob_name):
    if not os.path.exists(ejudge_downloads_path):
        return 0

    submits = [EjudgeSubmit.load(filename) for filename in
               glob.glob(f"{ejudge_downloads_path}/{ejudge_prob_prefix(contest_id, prob_name)}_*.*")]
    if len(submits) == 0:
        return 0

    submits.sort(key=lambda submit: submit.run_id, reverse=True)

    return submits[0].run_id


def oks_on_disk_count(contest_id, prob_name, language: Language):
    if not os.path.exists(ejudge_downloads_path):
        return 0

    return len(glob.glob(f"{ejudge_downloads_path}/{ejudge_prob_prefix(contest_id, prob_name)}_*{languages.file_extension(language)}"))


def analyze_problem(contest_id, prob_name,
                    similarity_threshold=60):

    prob_description = f"{contest_topic(contest_id)}-{prob_name}"

    last_ok = last_ok_on_disk_run_id(contest_id, prob_name)
    oks_downloaded_count = download_all_oks(contest_id, prob_name, last_ok)
    logging.info(f"Downloaded {oks_downloaded_count} new oks for {prob_description}")

    urls = []
    for lang in languages.supported_languages:
        prob_oks = oks_downloaded_count \
                   + oks_on_disk_count(contest_id, prob_name, lang)

        if prob_oks <= 1:
            logging.info(f"Not enough solutions found for {prob_description}-{lang}: {prob_oks}")
            continue

        params = moss.MossParameters(). \
            with_path(f"{ejudge_downloads_path}/{ejudge_prob_prefix(contest_id, prob_name)}_*{languages.file_extension(lang)}"). \
            with_language(lang). \
            with_experimental(). \
            with_comment(f"{prob_description}-{languages.name(lang)}"). \
            to_cli()

        url = moss.evaluate(params)
        assert url.startswith("http://moss.stanford.edu/results")

        moss.visualize(moss_url=url,
                       similarity_threshold=similarity_threshold,
                       transformation_regexp=f".+_.+_(.+)_(.+){languages.file_extension(lang)}",
                       save_to="results")

        urls.append(url)

    return urls
