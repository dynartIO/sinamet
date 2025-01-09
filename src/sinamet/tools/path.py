from pathlib import Path

def templatepath(file):
    return Path(file).parent / "template"

def datapath(file):
    return Path(file).parent / "data"


def buildpath(file):
    return Path(file).parent / "build"


def imgpath(file):
    return Path(file).parent / "img"


def cachepath(file):
    return Path(file).parent / "cache"


def buildhtmlpath(file):
    return buildpath(file) / ("%s.html" % Path(file).stem)


def cachehtmlpath(file):
    return cachepath(file) / ("%s.html" % Path(file).stem)


def makepath(file, folder=None, ext=None):
    mypath = Path(file).parent
    if folder is not None:
        mypath = mypath / folder
    if ext is not None:
        if not ext.startswith("."):
            ext = "." + ext
        mypath = mypath / ("%s%s" % (Path(file).stem, ext))
    return mypath