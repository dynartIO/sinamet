import hashlib
import base64
import unicodedata
import re


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


def minimize(string: str) -> str:
    """Renvoie une chaine sans accents, ni caractères spéciaux, ni espace en miniscule"""
    special_characters: dict[str, str] = {
            'æ': 'ae',
            'œ': 'oe',
            'ß': 'ss',
    }
    nfkd_form = unicodedata.normalize('NFKD', string.lower())
    unicode_lst = [c for c in nfkd_form if not unicodedata.combining(c)]
    unicode_str = u''.join([special_characters[c] if c in special_characters else c
                            for c in unicode_lst])
    return re.sub('[^a-z0-9]', '', unicode_str)
