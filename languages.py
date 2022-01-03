from enum import Enum


class Language(Enum):
    CPP = 1
    PYTHON = 2


supported_languages = [
    Language.CPP,
    Language.PYTHON
]


def file_extension(lang):
    if lang == Language.CPP:
        return ".cpp"

    if lang == Language.PYTHON:
        return ".py"

    raise ValueError(f"Unexpected language: {lang}")


def moss_lang_name(lang):
    if lang == Language.CPP:
        return "cc"

    if lang == Language.PYTHON:
        return "python"

    raise ValueError(f"Unexpected language: {lang}")


def name(lang):
    if lang == Language.CPP:
        return "C++"

    if lang == Language.PYTHON:
        return "Python"

    raise ValueError(f"Unexpected language: {lang}")
