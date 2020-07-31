import textwrap
from collections import defaultdict
from unicodedata import east_asian_width
from honahlee.utils.misc import to_str, inherits_from
from django.core.validators import validate_email as django_validate_email
from django.core.exceptions import ValidationError as DjangoValidationError

def wrap(text, width=None, indent=0):
    """
    Safely wrap text to a certain number of characters.

    Args:
        text (str): The text to wrap.
        width (int, optional): The number of characters to wrap to.
        indent (int): How much to indent each line (with whitespace).

    Returns:
        text (str): Properly wrapped text.

    """
    width = width if width else 78
    if not text:
        return ""
    indent = " " * indent
    return to_str(textwrap.fill(text, width, initial_indent=indent, subsequent_indent=indent))


# alias - fill
fill = wrap


def display_len(target):
    """
    Calculate the 'visible width' of text. This is not necessarily the same as the
    number of characters in the case of certain asian characters. This will also
    strip MXP patterns.

    Args:
        target (any): Something to measure the length of. If a string, it will be
            measured keeping asian-character and MXP links in mind.

    Return:
        int: The visible width of the target.

    """
    # Would create circular import if in module root.
    from mudslide.utils.ansi import ANSI_PARSER

    if inherits_from(target, str):
        # str or ANSIString
        target = ANSI_PARSER.strip_mxp(target)
        target = ANSI_PARSER.parse_ansi(target, strip_ansi=True)
        extra_wide = ("F", "W")
        return sum(2 if east_asian_width(char) in extra_wide else 1 for char in target)
    else:
        return len(target)


def string_partial_matching(alternatives, inp, ret_index=True):
    """
    Partially matches a string based on a list of `alternatives`.
    Matching is made from the start of each subword in each
    alternative. Case is not important. So e.g. "bi sh sw" or just
    "big" or "shiny" or "sw" will match "Big shiny sword". Scoring is
    done to allow to separate by most common demoninator. You will get
    multiple matches returned if appropriate.

    Args:
        alternatives (list of str): A list of possible strings to
            match.
        inp (str): Search criterion.
        ret_index (bool, optional): Return list of indices (from alternatives
            array) instead of strings.
    Returns:
        matches (list): String-matches or indices if `ret_index` is `True`.

    """
    if not alternatives or not inp:
        return []

    matches = defaultdict(list)
    inp_words = inp.lower().split()
    for altindex, alt in enumerate(alternatives):
        alt_words = alt.lower().split()
        last_index = 0
        score = 0
        for inp_word in inp_words:
            # loop over parts, making sure only to visit each part once
            # (this will invalidate input in the wrong word order)
            submatch = [
                last_index + alt_num
                for alt_num, alt_word in enumerate(alt_words[last_index:])
                if alt_word.startswith(inp_word)
            ]
            if submatch:
                last_index = min(submatch) + 1
                score += 1
            else:
                score = 0
                break
        if score:
            if ret_index:
                matches[score].append(altindex)
            else:
                matches[score].append(alt)
    if matches:
        return matches[max(matches)]
    return []


def validate_email_address(emailaddress):
    """
    Checks if an email address is syntactically correct. Makes use
    of the django email-validator for consistency.

    Args:
        emailaddress (str): Email address to validate.

    Returns:
        bool: If this is a valid email or not.

    """
    try:
        django_validate_email(str(emailaddress))
    except DjangoValidationError:
        return False
    except Exception:
        # logger.log_trace()
        return False
    else:
        return True
