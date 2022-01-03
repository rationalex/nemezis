import ejudge
import moss

import logging
import os

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))


def problem_range(first, last):
    return (chr(char_num) for char_num in range(ord(first), ord(last) + 1))


if __name__ == "__main__":

    # problems = {
    #     41301: problem_range('A', 'I'),
    #     41302: problem_range('A', 'F'),
    #     41304: problem_range('A', 'G'),
    #     41305: problem_range('A', 'G'),
    #     41306: problem_range('A', 'H'),
    # }
    #
    parallel_name = "2+"

    problems = {
        41203: problem_range('B', 'D'),
    }

    with open(f"{parallel_name}.moss_results", "w") as fout:
        for contest_id in problems.keys():
            contest_topic = ejudge.contest_topic(contest_id)
            for prob in problems[contest_id]:
                moss_urls = ejudge.analyze_problem(contest_id, prob,
                                                   similarity_threshold=60)

                for moss_url in moss_urls:
                    moss.save_report(moss_url, f"{parallel_name}-{contest_topic}-{prob}.html")

                    print(f"{contest_topic}-{prob}: {moss_url}",
                          file=fout)
