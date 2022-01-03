import logging
import os
import shutil
import subprocess
import time
import urllib.request

import languages


def with_key(key):
    if key is None:
        return ""
    return f"{key} "


def with_key_val(key, val):
    if val is None:
        return ""
    else:
        return f"{key} {val} "


class MossParameters:
    lang = "cc"
    path = "."

    experimental = None
    code_repeat_limit = None
    comment = None

    def __init__(self):
        pass

    def with_language(self, language):
        self.lang = languages.moss_lang_name(language)
        return self

    def with_path(self, path):
        self.path = path
        return self

    def with_experimental(self):
        self.experimental = "-x"
        return self

    def with_common_code_repeats_at_least(self, times):
        self.code_repeat_limit = times
        return self

    def with_comment(self, comment):
        self.comment = f'"{comment}"'
        return self

    def to_cli(self):
        return f"{with_key(self.experimental)}" \
               f"{with_key_val('-l', self.lang)}" \
               f"{with_key_val('-m', self.code_repeat_limit)}" \
               f"{with_key_val('-c', self.comment)}" \
               f"{with_key(self.path)}"


def extract_url_from_moss_response(moss_response):
    return moss_response[moss_response.find("http"):]


def evaluate(params):
    cmd = f"./moss.pl {params}"
    logging.info(f"{cmd}")

    backoff = 10  # seconds
    while True:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        out, err = proc.communicate()
        proc.wait()

        resp = out.decode("utf-8")
        logging.debug(resp)

        moss_url = extract_url_from_moss_response(resp)
        if moss_url == "":
            logging.info(f"Moss connection refused, starting backoff for {backoff} seconds")
            time.sleep(backoff)
            backoff *= 2
        else:
            break

    return moss_url


def visualize(moss_url, transformation_regexp, similarity_threshold, save_to=None):
    if save_to is None:
        save_to = "."

    cmd = f"mossum -r -p {similarity_threshold} -t \"{transformation_regexp}\" {moss_url}"
    logging.info(f"{cmd}")
    subprocess.run(cmd, stdout=subprocess.PIPE, shell=True)

    if save_to == ".":
        return

    subprocess.run(["mkdir", "-p", save_to],
                   stdout=subprocess.PIPE)

    for file in os.listdir("."):
        if file.endswith(".png") or file.endswith(".txt"):
            shutil.move(file, os.path.join(save_to, file))

    return


def save_report(moss_url, name):
    with urllib.request.urlopen(moss_url) as response, open(name, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)
