#!/usr/bin/env python
# vim: set fileencoding=utf-8:

"""
A script for inkshedding.
"""

import datetime
import os
import re
import subprocess

from contextlib import contextmanager


BASE_TEMPLATE = """
% {title}
% {author}
% {date}

{extra_content}
""".lstrip()

GLOBAL_DIRECTIVES = {
    'author': 'Eddie Antonio Santos',
}

# Need templates for contexts:
#  - English:
#    - Reading reflection
#    - Idea collection
# TODO: Make this a declarative file format. YAML, JSON or INI.
templates = {
    'engl': {
        'reading': {
            # The actual title of the inkshed.
            'title':        "{number} — {work_title}",
            # TODO: use alternative format when AugmentedStr is working fine
            # and dandy.
            'filename':     "{work_title}-{zeroed_number}", #"{work_title:|title,dashed}-{zeroed_number}",
            'dir':          'inksheds',
            'fulldir':      '/Users/eddieantonio/Documents/School/Engl/',

            # Temporary! Make this a callable!
            'work_title':   'Skim'
        },

        'idea': {
            # Herp derp derp
            'title': "Idea collection: {title}",
            'dir': '{paper}'
        },

        'basedir': '{basedir}/Engl'
    },

    'eas': {
        'idea': {
        },
    },

    'math': {},
    'ling': {},
    'relig': {},
}


def default_context():
    "Returns the fallback context."
    return ('engl', 'reading')


def format_todays_date():
    """
    Returns today's date in: "Month day, Year" format.
    """
    today = datetime.datetime.now()
    # Note: '%e' is a POSIX extension.
    return "{:%B %e, %y}".format(today)


def get_context_from_dir():
    """
    Automatically gets context based on the current working directory.
    """
    # TODO: Haha, I lied, suckah!
    return default_context()


def global_directives():
    directives = {
        'date': format_todays_date(),
        'extra_content': ''
    }

    directives.update(GLOBAL_DIRECTIVES)
    return directives


def dynamic_directives():
    # TODO: Figure out from directory regex.
    number = 0
    return {
        'zeroed_number': number,
        'number': number + 1,
    }


class AugmentedStr(str):
    """
    Augments string format by adding the `|` character after the type
    conversion. This allows string methods to be used to filter the string.

    >>> s = AugmentedStr('Hello World!     ')
    >>> print("{0:>30|strip,lower,dashed} ***".format(s))
                      hello-world! ***
    """

    def __format__(self, fmt):
        parts = fmt.split('|')

        # Split out the parts
        if len(parts) == 2:
            strfmt, methods = parts
        else:
            strfmt, methods = parts[0], ''

        method_names = methods.split(',')
        if method_names[0] == '':
            # Unable to extract any methods :C
            method_names = []

        # Applies the method with the given name and returns an AugmentedString.
        apply_method = lambda orig, name: AugmentedStr(getattr(orig, name)())

        # Apply all of the methods in sequence to the string.
        result = reduce(apply_method, method_names, self)

        # Delegate to builtin str format.
        return str.__format__(result, strfmt)

    def dashed(self, sep=None):
        """
        Returns a 'dashed' copy of the strings; e.g., whitespace replaced with
        dashes. Good for formatting slugs.

        >>> AugmentedStr('Boy howdee!').dashed()
        'Boy-howdee!'
        """
        return '-'.join(self.split())



def format_template(context):
    cat, subcat = context

    non_directives = {'dir', 'fulldir', 'date', 'number', 'zeroed_number'}

    # Prepare the directives from all sources.
    directives = global_directives()
    directives.update(dynamic_directives())
    directives.update(templates[cat][subcat])

    # TODO: Use augmented strings.

    # Do parameter substitution for formatted directives.
    formatted_directives = {}
    for name, directive in directives.items():
        # Skip non-directives
        if name in non_directives:
            continue

        formatted_directives[name] = directive.format(**directives)

    # Add all formatted/paramatterized directives to directives.
    directives.update(formatted_directives)

    return BASE_TEMPLATE.format(**directives)


def launch_editor(filename, default_editor='vi'):
    """
    Opens the filename in the users default editor.
    """
    editor = os.getenv('VISUAL') or os.getenv('EDITOR', default_editor)

    args = [editor, filename]

    # Go to the end of the file in Vim.
    if editor == 'vim':
        args.append('+norm G')

    return subprocess.call(args)


@contextmanager
def cd(directory):
    """
    Executes the statement in the given directory.
    """
    original_dir = os.getcwd()
    os.chdir(directory)
    yield
    os.chdir(original_dir)


def get_filename_for_context(_unused):
    # TODO: Finish this:
    return "/Users/eddieantonio/Documents/School/Engl/inksheds/", "test.md"


def start_inkshed(context, contents):
    directory, filename = get_filename_for_context(context)

    with cd(directory):
        with open(filename, 'w') as markdown:
            markdown.write(contents)
        launch_editor(filename)


def main():
    """
    Main function. Determines context from directory and creates a new file.
    """
    context = get_context_from_dir()
    file_contents = format_template(context)

    # Changes directory and starts the editor with the new file.
    start_inkshed(context, file_contents)


if __name__ == '__main__':
    exit(main())
