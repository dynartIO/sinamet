import hashlib
import base64
import re
import unidecode


def hexhash(string, length = 30):
    return hashlib.sha224( \
        str(string).encode('utf-8')).hexdigest()[0:length]


def alphanumhash(*content, length=32):
    """Return 0-9a-z hash string"""
    if length > 86:
        raise ValueError("Too high length=%s (max=86)" % length)
    mycontentstr = "/".join([str(c) for c in content])
    mycontent_hashed = str(mycontentstr).encode('utf-8')
    hash_filename = hashlib.sha512(mycontent_hashed).digest()
    myhash = str(base64.b64encode(hash_filename)).lower().replace("/","0").replace("+","1")[2:2 + length]
    return myhash


def minimize(string):
    """Renvoie une chaine sans accent, ni caractères spéciaux, ni espacen en miniscule"""
    return re.sub(r'\W+', '', unidecode.unidecode(string).lower())