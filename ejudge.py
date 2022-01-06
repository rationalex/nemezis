from languages import Language
import languages
import files
import moss
import secret
import web_navigation

import selenium.common.exceptions
from selenium.webdriver.common.by import By

from dataclasses import dataclass

import glob
import logging
import os
import os.path
from pathlib import Path
import re
import shutil

ejudge_url = "https://ejudge.lksh.ru"

directory_name = "ejudge"
contest_infos_path = os.path.join(directory_name, "contest_info")


def extract_SID(url):
    return url.split("=")[1].split("&")[0]


def extract_run_id(url):
    i = url.find("run_id=")
    if i == -1:
        return ""

    return int(url[i + 7:])


def open_ejudge_login_page_and_login():
    serve_control_url = f"{ejudge_url}/cgi-bin/serve-control"

    web_navigation.browser.get(serve_control_url)

    login = web_navigation.browser.find_element(By.NAME, "login")
    password = web_navigation.browser.find_element(By.NAME, "password")
    submit = web_navigation.browser.find_element(By.NAME, "submit")

    login.send_keys(secret.login)
    password.send_keys(secret.password)

    submit.click()


def go_to_judges(contest_id):
    sid = extract_SID(web_navigation.browser.current_url)
    contest_judge_url = f"{ejudge_url}/cgi-bin/new-judge?SID={sid}&action=3&contest_id={contest_id}"
    web_navigation.browser.get(contest_judge_url)


url_replacements = {
    ' ': "+",
    '=': "%3D",
    '&': "%26",
}


@dataclass
class ProblemInfo:
    parallel_name: str
    contest_id: int
    contest_topic: str
    problem_name: str

    def __str__(self):
        return f"{self.parallel_name}-{self.contest_topic}-{self.problem_name}"

    def to_path(self):
        return f"{self.parallel_name}/{self.contest_topic.replace(' ', '-')}/{self.problem_name}"


@dataclass
class EjudgeSubmit:
    username: str
    run_id: int
    filepath: str
    language: Language

    @staticmethod
    def load(path):
        filename = path.split('/')[-1]
        username, run_filename = filename.split('_')

        for lang in languages.supported_languages:
            extension_idx = run_filename.find(languages.file_extension(lang))
            if extension_idx != -1:
                run_id = int(run_filename[:extension_idx])
                submit_lang = lang
                break
        else:
            raise ValueError(f"Language of submit {run_filename} is not supported")

        return EjudgeSubmit(username=username,
                            run_id=run_id,
                            language=submit_lang,
                            filepath=path)


def url_safe(s):
    for bad in url_replacements.keys():
        s = s.replace(bad, url_replacements[bad])
    return s


def submits_to_check_filter(prob_name, later_than=-1, show_disqualified=True):
    status_filter = f"(status==OK || status==PR) && latest"
    if show_disqualified:
        status_filter = f"({status_filter}) || (status==DQ)"

    prob_filter = f"({status_filter}) && id > {later_than} && prob==\"{prob_name}\""
    return url_safe(prob_filter)


def problem_filter(prob_name):
    return url_safe(f"prob==\"{prob_name}\"")


# should be used only when on judges page
def apply_filter(filter):
    sid = extract_SID(web_navigation.browser.current_url)
    judge_url = f"{ejudge_url}/cgi-bin/new-judge?SID={sid}&filter_expr={filter}&filter_first_run=0&filter_last_run=-1"
    web_navigation.browser.get(judge_url)


def load_earliest_ok_page():
    ok_id_xpath = "/html/body/div[@id='main-cont']/div[@id='container']/table[@class='b1'][1]/tbody/tr[2]/td[@class='b1'][1]"
    # sometimes admin submissions have prepending # symbols to distinguish them from contestants' solutions
    ok_id = int(web_navigation.browser.find_element(By.XPATH, ok_id_xpath).text.strip('#'))

    username_xpath = "/html/body/div[@id='main-cont']/div[@id='container']/table[@class='b1'][1]/tbody/tr[2]/td[@class='b1'][3]"
    username = web_navigation.browser.find_element(By.XPATH, username_xpath).text

    ok_link_xpath = "/html/body/div[@id='main-cont']/div[@id='container']/table[@class='b1'][1]/tbody/tr[2]/td[@class='b1'][8]/a"
    ok_link = web_navigation.browser.find_element(By.XPATH, ok_link_xpath)
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


# contest_web_navigation.browser should be web_navigation.browser opened on contest judge page
def load_earliest_ok(problem_info: ProblemInfo, later_than=None, show_disqualified=True):
    if later_than is None:
        later_than = -1

    open_ejudge_login_page_and_login()

    go_to_judges(problem_info.contest_id)

    apply_filter(submits_to_check_filter(prob_name=problem_info.problem_name,
                                         later_than=later_than,
                                         show_disqualified=show_disqualified))

    earliest_ok_id, username = load_earliest_ok_page()

    lang_xpath = "/html/body/div[@id='main-cont']/div[@id='container']/div[@id='info-brief']/div[@class='table-scroll']/table[@class='table']/tbody/tr[2]/td[8]/a"
    lang = parse_language(web_navigation.browser.find_element(By.XPATH, lang_xpath).text)

    download_button_xpath = "/html/body/div[@id='main-cont']/div[@id='container']/div[@id='info-brief']/div[@id='brief-actions']/p/a[2]"
    download_button = web_navigation.browser.find_element(By.XPATH, download_button_xpath)
    download_button.click()

    return earliest_ok_id, username, lang


def download_all_new_oks(problem_info, later_than=-1, disqualified_too=True):
    Path(directory_name).mkdir(parents=True, exist_ok=True)

    ok_id = later_than
    ok_filepaths = []
    while True:
        try:
            # TODO: instead of loading earliest OK check for missing downloaded oks in case we change some query parameters
            # e.g. we choose to add DQ'd submits
            ok_id, username, lang = load_earliest_ok(problem_info=problem_info,
                                                     later_than=ok_id,
                                                     show_disqualified=disqualified_too)

            ok_filename = f"{str(ok_id).rjust(6, '0')}{languages.file_extension(lang)}"

            while not os.path.exists(ok_filename):
                pass

            logging.info(f"Downloaded {problem_info}-{ok_id}")

            problem_directory = os.path.join(directory_name, problem_info.to_path())
            Path(problem_directory).mkdir(parents=True, exist_ok=True)

            ok_path = os.path.join(f"{problem_directory}", f"{username.replace(' ', '-')}_{ok_filename}")
            shutil.move(ok_filename, ok_path)

            ok_filepaths.append(ok_path)
        except selenium.common.exceptions.NoSuchElementException:
            break
        except Exception as e:
            logging.info(e)
            break

    return ok_filepaths


def contest_topic(contest_id):
    # TODO: cache contest_topic results to file to reduce browser calls
    open_ejudge_login_page_and_login()
    go_to_judges(contest_id)

    head_xpath = "/html/body/div[@id='main-cont']/div[@id='container']/div[@id='header']/h1"
    admin_info = re.search("\[(.+?)\]", web_navigation.browser.find_element(By.XPATH, head_xpath).text).group(1)
    contest_name = admin_info.split(',')[2]

    return contest_name.split('.')[-1].strip()


def contest_problems_info_path(contest_id):
    return os.path.join(contest_infos_path, f"{contest_id}-{contest_topic(contest_id).replace(' ', '_')}.problems")


def try_load_contest_problem_names(contest_id):
    info_path = contest_problems_info_path(contest_id)
    return files.try_read_json_array(info_path)


# we assume that problems have names from A to Z
def get_contest_problem_names(contest_id):
    problems = try_load_contest_problem_names(contest_id)
    if problems is not None:
        return problems

    problems = []
    for problem_letter in (chr(c) for c in range(ord('A'), ord('Z') + 1)):
        open_ejudge_login_page_and_login()
        go_to_judges(contest_id)
        apply_filter(problem_filter(problem_letter))

        prob_name_xpath = "/html/body/div[@id='main-cont']/div[@id='container']/table[@class='b1'][1]/tbody/tr[2]/td[@class='b1'][4]"
        try:
            prob_name = web_navigation.browser.find_element(By.XPATH, prob_name_xpath).text
        except:
            continue

        problems.append(prob_name)

    files.write_json_array(problems, contest_problems_info_path(contest_id))
    return problems


def count_oks_downloaded(info: ProblemInfo, lang):
    return len(
        glob.glob(f"{directory_name}/{info.to_path()}/*{languages.file_extension(lang)}"))


def last_ok_on_disk_run_id(info: ProblemInfo):
    if not os.path.exists(directory_name):
        return 0

    submits = [EjudgeSubmit.load(filename) for filename in
               glob.glob(f"{directory_name}/{info.to_path()}/*.*")]
    if len(submits) == 0:
        return 0

    submits.sort(key=lambda submit: submit.run_id, reverse=True)

    return submits[0].run_id


def analyze_problem(info: ProblemInfo,
                    similarity_threshold=60,
                    new_oks_only=True):

    problem_description = f"{info.parallel_name}-{info.contest_topic}-{info.problem_name}"

    last_ok = last_ok_on_disk_run_id(info)
    new_ok_filepaths = download_all_new_oks(info,
                                            later_than=last_ok,
                                            disqualified_too=True)

    logging.info(f"Downloaded {len(new_ok_filepaths)} new oks for {problem_description}")

    urls = []
    for lang in languages.supported_languages:
        prob_lang_oks = count_oks_downloaded(info, lang)

        if prob_lang_oks <= 1:
            logging.info(f"Not enough solutions found for {problem_description}-{lang}: {prob_lang_oks}")
            continue

        if new_oks_only and len(new_ok_filepaths) == 0:
            logging.info(f"No new solutions found for {problem_description}-{lang}")
            continue

        params = moss.MossParameters(). \
            with_path(
            f"{directory_name}/{info.to_path()}/*{languages.file_extension(lang)}"). \
            with_language(lang). \
            with_experimental(). \
            with_comment(f"{problem_description}-{languages.name(lang)}"). \
            to_cli()

        url = moss.evaluate(params)
        assert url.startswith("http://moss.stanford.edu/results")

        moss.visualize(moss_url=url,
                       similarity_threshold=similarity_threshold,
                       transformation_regexp=f".+/.+/(.+)/(.+){languages.file_extension(lang)}",
                       save_to=f"moss/mossum/{info.parallel_name}")

        urls.append((lang, url))

    return urls
