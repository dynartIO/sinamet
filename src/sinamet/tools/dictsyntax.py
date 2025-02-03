from typing import Any

import sys

from ast import literal_eval

r = 'results'
s = 'sets'
g = 'graphicsinfo'


def dictinit(sets, *args):
    data_dict = {}
    data_dict[args[0]] = sets
    for a in args[1:]:
        data_dict[a] = {}
    return data_dict


def dictvalue0(listp):
    return {p["namefield"]: p["value0"] for p in listp if p["typefield"] not in ["title", "empty"]}


def dictdefaultvalues(listp):
    return {p["namefield"]: p["defaultvalue"] for p in listp if p["typefield"] not in ["title", "empty"]}


def listnamesfields(listp):
    return [p["namefield"] for p in listp if p["typefield"] not in ["title", "empty"]]


def check_argv(default_params: Any = None) -> Any:
    if len(sys.argv) > 1:
        return literal_eval(sys.argv[1])
    return default_params
