import textwrap
from unicodedata import east_asian_width
from honahlee.utils.misc import to_str, inherits_from


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
