import re

from mudslide.utils.ansi import ANSI_PARSER
from mudslide.utils.ansi import ANSIString


def clean_and_ansi(input_text, thing_name="Name"):
    if not input_text:
        raise ValueError(f"{thing_name} must not be empty!")
    input_text = input_text.strip()
    if '|' in input_text and not input_text.endswith('|n'):
        input_text += "|n"
    colored_text = ANSIString(input_text)
    clean_text = str(colored_text.clean())
    if '|' in clean_text:
        raise ValueError(f"Malformed ANSI in {thing_name}.")
    return clean_text, colored_text


def tabular_table(word_list=None, field_width=26, line_length=78, output_separator=" ", truncate_elements=True):
    """
    This function returns a tabulated string composed of a basic list of words.
    """
    if not word_list:
        word_list = list()
    elements = [ANSIString(entry) for entry in word_list]
    if truncate_elements:
        elements = [entry[:field_width] for entry in elements]
    elements = [entry.ljust(field_width) for entry in elements]
    separator_length = len(output_separator)
    per_line = line_length / (field_width + separator_length)
    result_string = ANSIString("")
    count = 0
    total = len(elements)
    for num, element in enumerate(elements):
        count += 1
        if count == 1:
            result_string += element
        elif count == per_line:
            result_string += output_separator
            result_string += element
            if not num+1 == total:
                result_string += '\n'
            count = 0
        elif count > 1:
            result_string += output_separator
            result_string += element
    return result_string


def sanitize_string(text=None, length=None, strip_ansi=False, strip_mxp=True, strip_newlines=True, strip_indents=True):
    if not text:
        return ''
    text = text.strip()
    if strip_mxp:
        text = ANSI_PARSER.strip_mxp(text)
    if strip_ansi:
        text = ANSIString(text).clean()
    if strip_newlines:
        for bad_char in ['\n', '%r', '%R', '|/']:
            text = text.replace(bad_char, '')
    if strip_indents:
        for bad_char in ['\t', '%t', '%T', '|-']:
            text = text.replace(bad_char, '')
    if length:
        text = text[:length]
    return text


def normal_string(text=None):
    return sanitize_string(text, strip_ansi=True)


def dramatic_capitalize(capitalize_string=''):
    capitalize_string = re.sub(r"(?i)(?:^|(?<=[_\/\-\|\s()\+]))(?P<name1>[a-z]+)",
                               lambda find: find.group('name1').capitalize(), capitalize_string.lower())
    capitalize_string = re.sub(r"(?i)\b(of|the|a|and|in)\b", lambda find: find.group(1).lower(), capitalize_string)
    capitalize_string = re.sub(r"(?i)(^|(?<=[(\|\/]))(of|the|a|and|in)",
                               lambda find: find.group(1) + find.group(2).capitalize(), capitalize_string)
    return capitalize_string


def penn_substitutions(input=None):
    if not input:
        return ''
    for bad_char in ['%r', '%R']:
        input = input.replace(bad_char, '|/')
    for bad_char in ['%t', '%T']:
        input = input.replace(bad_char, '|-')
    return input


SYSTEM_CHARACTERS = ('/', '|', '=', ',')


def sanitize_name(name, system_name):
    name = sanitize_string(name)
    if not name:
        raise ValueError("%s names must not be empty!" % system_name)
    for char in SYSTEM_CHARACTERS:
        if char in name:
            raise ValueError("%s is not allowed in %s names!" % (char, system_name))
    return name


def partial_match(match_text, candidates):
    candidate_list = sorted(candidates, key=lambda item: len(str(item)))
    for candidate in candidate_list:
        if match_text.lower() == str(candidate).lower():
            return candidate
        if str(candidate).lower().startswith(match_text.lower()):
            return candidate


def mxp(text="", command="", hints=""):
    if text:
        return ANSIString("|lc%s|lt%s|le" % (command, text))
    else:
        return ANSIString("|lc%s|lt%s|le" % (command, command))


class Speech(object):
    """
    This class is used for rendering an entity's speech to other viewers.
    It is meant to render speech from a player or character. The output replicates MUSH-style
    speech from varying input. Intended output:

    If input = ':blah.', output = 'Character blah.'
    If input = ';blah.', output = 'Characterblah.'
    If input = |blah', output = 'blah'
    If input = 'blah.', output = 'Character says, "Blah,"'

    """
    re_speech = re.compile(r'(?s)"(?P<found>.*?)"')
    re_name = re.compile(r"\^\^\^(?P<thing_id>\d+)\:(?P<thing_name>[^^]+)\^\^\^")
    speech_dict = {':': 1, ';': 2, '^': 3, '"': 0, "'": 0}

    def __init__(self, speaker=None, speech_text=None, alternate_name=None, title=None, mode='ooc', targets=None,
                 rendered_text=None, action_string="says", controller="character", color_mode='channel'):

        self.controller = athanor.CONTROLLER_MANAGER.get(controller)
        if targets:
            self.targets = [f'^^^{char.id}:{char.key}^^^' for char in targets]
        else:
            self.targets = []
        self.mode = mode
        self.color_mode = color_mode
        self.title = title
        self.speaker = speaker
        self.action_string = action_string

        if alternate_name:
            self.alternate_name = alternate_name
            self.display_name = alternate_name
            self.markup_name = alternate_name
        else:
            self.display_name = str(speaker)
            self.alternate_name = False
            self.markup_name = f'^^^{speaker.id}:{speaker.key}^^^'

        speech_first = speech_text[:1]
        if speech_first in self.speech_dict:
            special_format = self.speech_dict[speech_first]
            speech_string = speech_text[1:]
        else:
            special_format = 0
            speech_string = speech_text

        self.special_format = special_format
        self.speech_string = speech_string

        if rendered_text:
            self.markup_string = rendered_text
        else:
            self.markup_string = self.controller.reg_names.sub(self.markup_names, self.speech_string)

    def markup_names(self, match):
        found = match.group('found')
        return f'^^^{self.controller.name_map[found.upper()].id}:{found}^^^'

    def __str__(self):
        str(self.demarkup())

    def monitor_display(self, viewer=None):
        if not viewer:
            return self.demarkup()
        if not self.alternate_name:
            return self.render(viewer)
        return_string = None
        if self.special_format == 0:
            return_string = f'({self.markup_name}){self.alternate_name} {self.action_string}, "{self.markup_string}"'
        elif self.special_format == 1:
            return_string = f'({self.markup_name}){self.alternate_name} {self.markup_string}'
        elif self.special_format == 2:
            return_string = f'({self.markup_name}){self.alternate_name}{self.markup_string}'
        elif self.special_format == 3:
            return_string = f'({self.markup_name}){self.markup_string}'
        if self.title:
            return_string = f'{self.title} {return_string}'

        return self.colorize(return_string, viewer)

    def render(self, viewer=None):
        if not viewer:
            return ANSIString(self.demarkup())
        return_string = None
        if self.special_format == 0:
            return_string = f'{self.markup_name} {self.action_string}, "{self.markup_string}|n"'
        elif self.special_format == 1:
            return_string = f'{self.markup_name} {self.markup_string}'
        elif self.special_format == 2:
            return_string = f'{self.markup_name}{self.markup_string}'
        elif self.special_format == 3:
            return_string = self.markup_string
        if self.title:
            return_string = f'{self.title} {return_string}'
        if self.mode == 'page' and len(self.targets) > 1:
            pref = f'(To {", ".join(self.targets)})'
            return_string = f'{pref} {return_string}'

        return self.colorize(return_string, viewer)

    def log(self):
        return_string = None
        if self.special_format == 0:
            return_string = f'{self.markup_name} {self.action_string}, "{self.markup_string}|n"'
        elif self.special_format == 1:
            return_string = f'{self.markup_name} {self.markup_string}'
        elif self.special_format == 2:
            return_string = f'{self.markup_name}{self.markup_string}'
        elif self.special_format == 3:
            return_string = self.markup_string
        if self.title:
            return_string = f'{self.title} {return_string}'
        if self.mode == 'page' and len(self.targets) > 1:
            pref = f'(To {", ".join(self.targets)}'
            return_string = f'{pref} {return_string}'
        return return_string

    def demarkup(self):
        return_string = None
        if self.special_format == 0:
            return_string = f'{self.display_name} {self.action_string}, "{self.speech_string}|n"'
        elif self.special_format == 1:
            return_string = f'{self.display_name} {self.speech_string}'
        elif self.special_format == 2:
            return_string = f'{self.display_name}{self.speech_string}'
        elif self.special_format == 3:
            return_string = self.speech_string
        if self.title:
            return_string = f'{self.title} {return_string}'
        return ANSIString(return_string)

    def colorize(self, message, viewer):
        viewer = viewer.get_account() if viewer and hasattr(viewer, 'get_account') else None
        colors = dict()
        styler = viewer.styler if viewer else athanor.STYLER(None)
        for op in ("quotes", "speech", "speaker", "self", 'other'):
            colors[op] = styler.options.get(f"{op}_{self.color_mode}", '')
            if colors[op] == 'n':
                colors[op] = ''

        quote_color = colors["quotes"]
        speech_color = colors["speech"]

        def color_speech(found):
            if not quote_color and not speech_color:
                return f'"{found.group("found")}"'
            if quote_color and not speech_color:
                return f'|{quote_color}"|n{found.group("found")}|n|{quote_color}"|n'
            if speech_color and not quote_color:
                return f'"|n|{speech_color}{found.group("found")}|n"'
            if quote_color and speech_color:
                return f'|{quote_color}"|n|{speech_color}{found.group("found")}|n|{quote_color}"|n'

        def color_names(found):
            data = found.groupdict()
            thing_name = data["thing_name"]
            if not viewer:
                return thing_name
            thing_id = int(data["thing_id"])
            if not (obj := self.controller.id_map.get(thing_id, None)):
                return thing_name
            custom = viewer.colorizer.get(obj, None)
            if custom and custom != 'n':
                return f"|n|{custom}{thing_name}|n"
            if obj == viewer and colors["self"]:
                return f"|n|{colors['self']}{thing_name}|n"
            if obj == self.speaker and colors['speaker']:
                return f"|n|{colors['speaker']}{thing_name}|n"
            return thing_name

        colorized_string = self.re_speech.sub(color_speech, message)
        colorized_string = self.re_name.sub(color_names, colorized_string)
        return colorized_string


def iter_to_string(iter):
    return ', '.join(str(i) for i in iter)
