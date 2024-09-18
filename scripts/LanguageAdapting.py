import re


def translate(name_lower: str):
    res = ""
    for c in name_lower:
        if c == "а":
            res += "a"
        elif c == "б":
            res += "b"
        elif c == "в":
            res += "v"
        elif c == "г":
            res += "g"
        elif c == "д":
            res += "d"
        elif c == "е":
            res += "e"
        elif c == "ё":
            res += "e"
        elif c == "ж":
            res += "zh"
        elif c == "з":
            res += "z"
        elif c == "и":
            res += "i"
        elif c == "й":
            res += "y"
        elif c == "к":
            res += "k"
        elif c == "л":
            res += "l"
        elif c == "м":
            res += "m"
        elif c == "н":
            res += "n"
        elif c == "о":
            res += "o"
        elif c == "п":
            res += "p"
        elif c == "р":
            res += "r"
        elif c == "с":
            res += "c"
        elif c == "т":
            res += "t"
        elif c == "у":
            res += "u"
        elif c == "ф":
            res += "f"
        elif c == "х":
            res += "h"
        elif c == "ц":
            res += "ts"
        elif c == "ч":
            res += "ch"
        elif c == "ш":
            res += "sh"
        elif c == "щ":
            res += "shch"
        elif c == "ъ":
            res += ""
        elif c == "ы":
            res += "y"
        elif c == "ь":
            res += ""
        elif c == "э":
            res += "e"
        elif c == "ю":
            res += "yu"
        elif c == "я":
            res += "ya"
        else:
            res += c
    return res


def generate_ozon_name(name: str, art):
    base_url = "https://www.ozon.ru/product/"
    name_lower = name.lower()
    name_sep = name_lower.replace(" ", "-")
    name_sep = re.sub(r'[^а-яА-Яa-zA-Z0-9-]', '', name_sep)
    return f"{base_url}{translate(name_sep)}-{art}/"
