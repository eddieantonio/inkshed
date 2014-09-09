#!/usr/bin/env python
# vim: set fileencoding=utf-8:

"""
A script for inkshedding.
"""

import ConfigParser
import argparse
import cPickle
import datetime
import os
import pickle
import re
import subprocess

from contextlib import contextmanager
from functools import reduce

BASE_TEMPLATE = """
% {title}
% {author}
% {date}

{extra_content}
""".lstrip()

DEFAULTS = {
    'basedir': os.path.expanduser('~'),
    'title': '{number} — {subject}',
}


class AugmentedStr(str):

    """
    Augments string format by adding the `|` character after the type
    conversion. This allows string methods to be used to filter the
    string.

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

        # Applies the method with the given name and returns an AugmentedStr.
        apply_method = lambda orig, name: AugmentedStr(getattr(orig, name)())

        # Apply all of the methods in sequence to the string.
        result = reduce(apply_method, method_names, self)

        # Delegate to builtin str format.
        return str.__format__(result, strfmt)

    def dashed(self, sep=None):
        """
        Returns a 'dashed' copy of the strings; e.g., whitespace
        replaced with dashes.

        >>> AugmentedStr('Boy howdee!').dashed()
        'Boy-howdee!'
        """
        return '-'.join(self.split())

    def slugify(self, sep='-'):
        """
        Like dashed, but also performs some additional normalization,
        including changing to lowercase.

        >>> s = AugmentedStr("I'm naïve at Iñtërnâtiônàlizætiøn!")
        >>> print(s.slugify())
        i-m-naïve-at-iñtërnâtiônàlizætiøn
        """

        # Splits the string, Unicode aware!
        splitter = re.compile(r'\W', re.UNICODE)

        # Ensure we have a Unicode string to make sure we don't mangle
        # those...
        unistr = self.decode('UTF-8')
        components = splitter.split(unistr.lower(), re.UNICODE)

        # Join only non-empty components.
        return sep.join(c for c in components if len(c)).encode('UTF-8')


def format_todays_date():
    """
    Returns today's date in: "Month day, Year" format.
    """
    today = datetime.datetime.now()
    # Note: '%e' is a POSIX extension.
    return "{:%B %e, %y}".format(today)


def global_directives():
    directives = {
        'date': format_todays_date(),
        'extra_content': ''
    }
    return directives


def format_context(context):
    """
    Returns a copy of the context in which parameter substitution using
    AugmentedStr has been performed.
    """
    # Items that should do NOT need to have parameter substitution.
    non_directives = {'dir', 'basedir', 'date', 'number', 'zeroed_number'}

    """
    # Use them augmented strings to do parameter substitution.
    aug_context = {key: AugmentedStr(value).format(**context)
            for key, value in context.items()
            if key not in non_directives}
    """

    # Convert all of the things to AugmentedStr to do nifty things with them
    # later...
    augmented_context = {key: AugmentedStr(val)
                         for key, val in context.items()}

    formatted_context = {}
    # Could have done this in a dict comp, but... this gives better error
    # messages.
    for key, value in augmented_context.items():
        if key in non_directives:
            continue
        formatted_context[key] = value.format(**augmented_context)

    return formatted_context


def format_template(context):
    """"
    Does parameter substitution for the context and returns the
    formatted template.
    """

    return BASE_TEMPLATE.format(**context)


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
def cd(directory, stay=False):
    """
    In a with statement, executes the block in the given directory. If
    `stay` is True, does not change the directory back.
    """
    original_dir = os.getcwd()
    os.chdir(directory)
    yield

    if not stay:
        os.chdir(original_dir)


def get_filename_for_context(context):
    """
    Returns a tuple of (dir, filename) from the FORMATTED context.

    >>> ctx = {'dir': '/Users/eddieantonio', 'filename': 'Skim-02'}
    >>> get_filename_for_context(ctx)
    ('/Users/eddieantonio', 'Skim-02.md')
    """
    assert 'dir' in context and 'filename' in context
    return context['dir'], context['filename'] + '.md'


def start_inkshed(context, contents):
    directory, filename = get_filename_for_context(context)

    with cd(directory):
        # TODO: Check if file exists!
        with open(filename, 'w') as markdown:
            markdown.write(contents)
        launch_editor(filename)


def default_config_path():
    "Returns the default configuration path."
    return os.path.expanduser('~/.inkshed.cfg')


def parse_config(category, config_location=None):
    "Parses the configuration file."

    if not config_location:
        config_location = default_config_path()

    parser = ConfigParser.ConfigParser()

    # Try reading from the given config.
    if not os.path.exists(config_location):
        raise ValueError("Could not read config from '%s': "
                         ' file does not exist.' % (config_location,))

    parser.read(config_location)
    # Parse out general settings.
    initial_config = {}
    initial_config.update(DEFAULTS)
    initial_config.update(parser.items('__general__'))
    initial_config.update(global_directives())

    # Get the category... fail if we get some Falsy value.
    category = category or initial_config.get('default')
    if not category:
        raise ValueError('No category given and no default in config')

    # Don't bother to parser further; the category doesn't exist so we
    # should just bail.
    if not parser.has_section(category):
        ValueError('Configuration (%s) lacks section for '
                   'category %s' % (config_location, category))

    # Parse the initial category.
    options = parser.items(category, raw=True)
    category_additions = parse_category(options, initial_config)
    initial_config.update(category_additions)

    return initial_config


def parse_category(category, initial_config):
    """
    >>> cat = {'dir': 'Engl/inksheds', 'subject': 'Skim'}
    >>> initial = {'basedir': '/Users/eddieantonio/'}
    >>> d = parse_category(cat, initial)
    >>> d['dir']
    '/Users/eddieantonio/Engl/inksheds'
    """

    assert 'basedir' in initial_config

    # Fill the additions with the category (for now...).
    additions = {}
    additions.update(category)

    # Add the relative directory to the category.
    if 'dir' in additions:
        basedir = initial_config['basedir']
        additions['dir'] = os.path.join(basedir, additions['dir'])

    additions['subject'] = additions.get('subject', '__unknown__')
    # TODO: parse out subject date strings...

    return additions


def context_from_current_dir(context):
    """
    Adds 'number' and 'zeroed_number' to the context, given the current
    directory AND subject!
    """
    assert 'dir' in context and 'subject' in context

    filename = '.inkshed.pickle'
    subject = context['subject']

    if not os.path.exists(filename):
        # Create the initial, empty context.
        config = {
            subject: {'number': 0}
        }
    else:
        with open(filename, 'rb') as f:
            config = cPickle.load(f)

    # Get either the config, or a new config.  Assume `number` will be
    # incremented in before the return of this function.
    additions = config.get(subject, {'number': 0})
    config[subject] = additions

    # Increment the subject.
    additions['number'] += 1

    # TODO: should writeback occur here?
    # Write back the config.
    with open(filename, 'wb') as f:
        cPickle.dump(config, f)

    # Add relative number -- not to be persisted
    additions['zeroed_number'] = additions['number'] - 1

    return additions


# TODO:
def parse_args(args=None):
    pass


class TemporaryArgs(object):
    "DELETE ME!"
    should_cd = False
    config_location = None
    category = 'engl'


def main():
    """
    Main function. Determines context from directory and creates a new
    file.
    """

    # Parse all things that need to be parsed.
    args = TemporaryArgs()
    context = parse_config(args.category, args.config_location)

    # Changes directory and starts the editor with the new file.
    with cd(context['dir'], stay=args.should_cd):
        context.update(context_from_current_dir(context))
        context.update(format_context(context))
        file_contents = format_template(context)

        start_inkshed(context, file_contents)


# Synopsis
#
#   inkshed [category [subject]] [-c/--cd]

# parse configs -> make context -> parse additonal configs -> parameter sub ->
# fill template -> launch editor
#

if __name__ == '__main__':
    exit(main())
