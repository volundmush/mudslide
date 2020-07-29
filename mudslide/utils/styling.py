import math, datetime
from django.conf import settings

from evennia.utils.evtable import EvTable
from evennia.utils.ansi import ANSIString
from evennia.utils.utils import lazy_property, class_from_module

class Styler:
    fallback = dict()
    loaded = False
    width = 78
    fallback_cache = dict()


    def __init__(self, viewer):
        """
        It's important to keep in mind that viewer can totally be None.
        """
        self.cache = dict()
        if viewer and hasattr(viewer, 'get_account'):
            self.viewer = viewer.get_account()
        else:
            self.viewer = None
        if not self.loaded:
            self.load()
        if self.viewer:
            self.options = self.viewer.options
        else:
            self.options = self.fallback

    @classmethod
    def load(cls):
        for key, data in settings.OPTIONS_ACCOUNT_DEFAULT.items():
            cls.fallback[key] = data[2]
        cls.width = settings.CLIENT_DEFAULT_WIDTH
        cls.loaded = True

    def styled_columns(self, columns):
        return f"|{self.options.get('column_names_color')}{columns}|n"

    def styled_table(self, *args, **kwargs):
        """
        Create an EvTable styled by on user preferences.

        Args:
            *args (str): Column headers. If not colored explicitly, these will get colors
                from user options.
        Kwargs:
            any (str, int or dict): EvTable options, including, optionally a `table` dict
                detailing the contents of the table.
        Returns:
            table (EvTable): An initialized evtable entity, either complete (if using `table` kwarg)
                or incomplete and ready for use with `.add_row` or `.add_collumn`.

        """
        border_color = self.options.get("border_color")
        column_color = self.options.get("column_names_color")

        colornames = ["|%s%s|n" % (column_color, col) for col in args]

        h_line_char = kwargs.pop("header_line_char", "~")
        header_line_char = ANSIString(f"|{border_color}{h_line_char}|n")
        c_char = kwargs.pop("corner_char", "+")
        corner_char = ANSIString(f"|{border_color}{c_char}|n")

        b_left_char = kwargs.pop("border_left_char", "||")
        border_left_char = ANSIString(f"|{border_color}{b_left_char}|n")

        b_right_char = kwargs.pop("border_right_char", "||")
        border_right_char = ANSIString(f"|{border_color}{b_right_char}|n")

        b_bottom_char = kwargs.pop("border_bottom_char", "-")
        border_bottom_char = ANSIString(f"|{border_color}{b_bottom_char}|n")

        b_top_char = kwargs.pop("border_top_char", "-")
        border_top_char = ANSIString(f"|{border_color}{b_top_char}|n")

        table = EvTable(
            *colornames,
            header_line_char=header_line_char,
            corner_char=corner_char,
            border_left_char=border_left_char,
            border_right_char=border_right_char,
            border_top_char=border_top_char,
            **kwargs,
        )
        return table

    def _render_decoration(
            self,
            header_text=None,
            fill_character=None,
            edge_character=None,
            mode="header",
            color_header=True,
            width=None,
            use_cache=True
    ):
        """
        Helper for formatting a string into a pretty display, for a header, separator or footer.

        Kwargs:
            header_text (str): Text to include in header.
            fill_character (str): This single character will be used to fill the width of the
                display.
            edge_character (str): This character caps the edges of the display.
            mode(str): One of 'header', 'separator' or 'footer'.
            color_header (bool): If the header should be colorized based on user options.
            width (int): If not given, the client's width will be used if available.
            use_cache (bool): If True, will fetch generated text from a cache if available.

        Returns:
            string (str): The decorated and formatted text.

        """
        # this tuple is used for the cache key.
        cache_id = (header_text, fill_character, edge_character, mode, color_header, width)

        # Retrieve from cache if relevant.
        if use_cache:
            if self.viewer:
                if (found := self.cache.get(cache_id, None)):
                    return found
            else:
                if (found := self.fallback_cache.get(cache_id, None)):
                    return found

        colors = dict()
        colors["border"] = self.options.get("border_color")
        colors["headertext"] = self.options.get(f"{mode}_text_color")
        colors["headerstar"] = self.options.get(f"{mode}_star_color")

        width = self.width
        if edge_character:
            width -= 2

        if header_text:
            if color_header:
                header_text = ANSIString(header_text).clean()
                header_text = ANSIString("|n|%s%s|n" % (colors["headertext"], header_text))
            if mode == "header":
                begin_center = ANSIString(
                    "|n|%s<|%s* |n" % (colors["border"], colors["headerstar"])
                )
                end_center = ANSIString("|n |%s*|%s>|n" % (colors["headerstar"], colors["border"]))
                center_string = ANSIString(begin_center + header_text + end_center)
            else:
                center_string = ANSIString("|n |%s%s |n" % (colors["headertext"], header_text))
        else:
            center_string = ""

        fill_character = self.options.get("%s_fill" % mode)

        remain_fill = width - len(center_string)
        if remain_fill % 2 == 0:
            right_width = remain_fill / 2
            left_width = remain_fill / 2
        else:
            right_width = math.floor(remain_fill / 2)
            left_width = math.ceil(remain_fill / 2)
        right_fill = ANSIString("|n|%s%s|n" % (colors["border"], fill_character * int(right_width)))
        left_fill = ANSIString("|n|%s%s|n" % (colors["border"], fill_character * int(left_width)))

        if edge_character:
            edge_fill = ANSIString("|n|%s%s|n" % (colors["border"], edge_character))
            main_string = ANSIString(center_string)
            final_send = (
                    ANSIString(edge_fill) + left_fill + main_string + right_fill + ANSIString(edge_fill)
            )
        else:
            final_send = left_fill + ANSIString(center_string) + right_fill

        # After going through all of this trouble, cache the result.
        if use_cache:
            if self.viewer:
                self.cache[cache_id] = final_send
            else:
                self.fallback_cache[cache_id] = final_send

        return final_send

    def styled_header(self, *args, **kwargs):
        """
        Create a pretty header.
        """

        if "mode" not in kwargs:
            kwargs["mode"] = "header"
        return self._render_decoration(*args, **kwargs)

    def styled_separator(self, *args, **kwargs):
        """
        Create a separator.

        """
        if "mode" not in kwargs:
            kwargs["mode"] = "separator"
        return self._render_decoration(*args, **kwargs)

    def styled_footer(self, *args, **kwargs):
        """
        Create a pretty footer.

        """
        if "mode" not in kwargs:
            kwargs["mode"] = "footer"
        return self._render_decoration(*args, **kwargs)

    @lazy_property
    def blank_footer(self):
        return self.styled_footer()

    @lazy_property
    def blank_separator(self):
        return self.styled_separator()

    @lazy_property
    def blank_header(self):
        return self.styled_header()

    time_formats = {
        'full': '%c',
        'standard': '%b %d %I:%M%p %Z',
    }

    def localize_timestring(self, time_data=None, time_format='standard', tz=None):
        if not time_data:
            time_data = datetime.datetime.utcnow()
        if not tz:
            tz = self.options.get('timezone')
        return time_data.astimezone(tz).strftime(time_format)
