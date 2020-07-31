# This file is basically just a dumb way to get around the Django settings issue for ANSIString...


class AnsiSettings:

    def __init__(self):
        # Mapping to extend Evennia's normal ANSI color tags. The mapping is a list of
        # tuples mapping the exact tag (not a regex!) to the ANSI convertion, like
        # `(r"%c%r", ansi.ANSI_RED)` (the evennia.utils.ansi module contains all
        # ANSI escape sequences). Default is to use `|` and `|[` -prefixes.
        self.COLOR_ANSI_EXTRA_MAP = []
        # Extend the available regexes for adding XTERM256 colors in-game. This is given
        # as a list of regexes, where each regex must contain three anonymous groups for
        # holding integers 0-5 for the red, green and blue components Default is
        # is r'\|([0-5])([0-5])([0-5])', which allows e.g. |500 for red.
        # XTERM256 foreground color replacement
        self.COLOR_XTERM256_EXTRA_FG = []
        # XTERM256 background color replacement. Default is \|\[([0-5])([0-5])([0-5])'
        self.COLOR_XTERM256_EXTRA_BG = []
        # Extend the available regexes for adding XTERM256 grayscale values in-game. Given
        # as a list of regexes, where each regex must contain one anonymous group containing
        # a single letter a-z to mark the level from white to black. Default is r'\|=([a-z])',
        # which allows e.g. |=k for a medium gray.
        # XTERM256 grayscale foreground
        self.COLOR_XTERM256_EXTRA_GFG = []
        # XTERM256 grayscale background. Default is \|\[=([a-z])'
        self.COLOR_XTERM256_EXTRA_GBG = []
        # ANSI does not support bright backgrounds, so Evennia fakes this by mapping it to
        # XTERM256 backgrounds where supported. This is a list of tuples that maps the wanted
        # ansi tag (not a regex!) to a valid XTERM256 background tag, such as `(r'{[r', r'{[500')`.
        self.COLOR_ANSI_XTERM256_BRIGHT_BG_EXTRA_MAP = []
        # If set True, the above color settings *replace* the default |-style color markdown
        # rather than extend it.
        self.COLOR_NO_DEFAULT = False
        self.CLIENT_DEFAULT_WIDTH = 78


settings = AnsiSettings()
