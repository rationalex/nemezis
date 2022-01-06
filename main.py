import ejudge
import files
import languages
import web_navigation

import os
import logging

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))


def contest_range(first, last):
    return range(first, last + 1)


# TODO: add e-maxx copypasta
# TODO: add cli-launch
# TODO: add moss-registration through cli
# TODO: don't count input reading as plagiarism. Possibly just remove it from source code?
# TODO: add cli-flag to compare submits from different problems (to check cross-group plagiarism)
# TODO: ignore disqualified submits that had OK later

if __name__ == "__main__":
    # parallel_contests = {
    #     "1+": contest_range(first=41101, last=41107),
    #     "2+": contest_range(first=41201, last=41207),
    #     "3+": contest_range(first=41301, last=41308),
    #     "4+": contest_range(first=41401, last=41407),
    #     "5+": contest_range(first=41501, last=41508),
    #     "6+": contest_range(first=41601, last=41608),
    #     "7+": contest_range(first=41701, last=41708),
    #     "8+": contest_range(first=41801, last=41808),
    #     "9+": contest_range(first=41901, last=41907),
    # }

    exam_contests = {
        # "1+": [41108],
        # "2+": [41208],
        # "3+": [41308],
        # "4+": [41408],
        # "5+": [41509],
        # "6+": [41609],
        # "7+": [41709],
        "8+": [41808],
    }

    parallel_contests = exam_contests

    web_navigation.start_browser()

    for parallel_name in parallel_contests.keys():
        results_filepath = f"moss/{parallel_name}.moss_results"
        files.create_directories_if_not(results_filepath)

        with open(results_filepath, "a") as fout:
            for contest_id in parallel_contests[parallel_name]:
                try:
                    contest_topic = ejudge.contest_topic(contest_id)
                    contest_problems = ejudge.get_contest_problem_names(contest_id)
                    # TODO: provide option to choose which problems to check
                    for prob_name in contest_problems:
                        problem_info = ejudge.ProblemInfo(parallel_name=parallel_name,
                                                          contest_id=contest_id,
                                                          contest_topic=contest_topic,
                                                          problem_name=prob_name)

                        moss_submits = ejudge.analyze_problem(info=problem_info,
                                                              similarity_threshold=20,
                                                              new_oks_only=True)

                        for lang, moss_url in moss_submits:
                            lang_name = languages.name(lang)

                            print(f"{contest_topic}-{prob_name}-{lang_name}: {moss_url}",
                                  file=fout)

                except IndexError:
                    logging.info(f"Contest {contest_id} doesn't exist")
                    continue

    web_navigation.browser.close()
