# Human friendly input/output in Python.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: June 3, 2015
# URL: https://humanfriendly.readthedocs.org

"""
Some generic notes about the table formatting functions in this module:

- These functions were not written with performance in mind (*at all*) because
  they're intended to format tabular data to be presented on a terminal. If
  someone were to run into a performance problem using these functions, they'd
  be printing so much tabular data to the terminal that a human wouldn't be
  able to digest the tabular data anyway, so the point is moot :-).

- These functions ignore ANSI escape sequences (at least the ones generated by
  the :mod:`~humanfriendly.terminal` module) in the calculation of columns
  widths. On reason for this is that column names are highlighted in color when
  connected to a terminal. It also means that you can use ANSI escape sequences
  to highlight certain column's values if you feel like it (for example to
  highlight deviations from the norm in an overview of calculated values).
"""

# Standard library modules.
import collections
import re

# Modules included in our package.
from humanfriendly.terminal import (
    ansi_strip,
    ansi_width,
    ansi_wrap,
    connected_to_terminal,
    find_terminal_size,
    HIGHLIGHT_COLOR,
)

# Compatibility with Python 2 and 3.
try:
    # Python 2.
    unicode_type = unicode
except NameError:
    # Python 3.
    unicode_type = str

# Compiled regular expression pattern to recognize table columns containing
# numeric data (integer and/or floating point numbers). Used to right-align the
# contents of such columns.
#
# Pre-emptive snarky comment: This pattern doesn't match every possible
# floating point number notation!?!1!1
#
# Response: I know, that's intentional. The use of this regular expression
# pattern has a very high DWIM level and weird floating point notations do not
# fall under the DWIM umbrella :-).
NUMERIC_DATA_PATTERN = re.compile(r'^\d+(\.\d+)?$')


def format_smart_table(data, column_names):
    """
    Render tabular data using the most appropriate representation.

    :param data: An iterable (e.g. a :func:`tuple` or :class:`list`)
                 containing the rows of the table, where each row is an
                 iterable containing the columns of the table (strings).
    :param column_names: An iterable of column names (strings).
    :returns: The rendered table (a string).

    If you want an easy way to render tabular data on a terminal in a human
    friendly format then this function is for you! It works as follows:

    - If the input data doesn't contain any line breaks the function
      :func:`format_pretty_table()` is used to render a pretty table. If the
      resulting table fits in the terminal without wrapping the rendered pretty
      table is returned.

    - If the input data does contain line breaks or if a pretty table would
      wrap (given the width of the terminal) then the function
      :func:`format_robust_table()` is used to render a more robust table that
      can deal with data containing line breaks and long text.
    """
    # Normalize the input in case we fall back from a pretty table to a robust
    # table (in which case we'll definitely iterate the input more than once).
    data = [normalize_columns(r) for r in data]
    column_names = normalize_columns(column_names)
    # Make sure the input data doesn't contain any line breaks (because pretty
    # tables break horribly when a column's text contains a line break :-).
    if not any(any('\n' in c for c in r) for r in data):
        # Render a pretty table.
        pretty_table = format_pretty_table(data, column_names)
        # Check if the pretty table fits in the terminal.
        table_width = max(map(ansi_width, pretty_table.splitlines()))
        num_rows, num_columns = find_terminal_size()
        if table_width <= num_columns:
            # The pretty table fits in the terminal without wrapping!
            return pretty_table
    # Fall back to a robust table when a pretty table won't work.
    return format_robust_table(data, column_names)


def format_pretty_table(data, column_names=None, horizontal_bar='-', vertical_bar='|'):
    """
    Render a table using characters like dashes and vertical bars to emulate borders.

    :param data: An iterable (e.g. a :func:`tuple` or :class:`list`)
                 containing the rows of the table, where each row is an
                 iterable containing the columns of the table (strings).
    :param column_names: An iterable of column names (strings).
    :param horizontal_bar: The character used to represent a horizontal bar (a
                           string).
    :param vertical_bar: The character used to represent a vertical bar (a
                         string).
    :returns: The rendered table (a string).

    Here's an example:

    >>> from humanfriendly.tables import format_pretty_table
    >>> column_names = ['Version', 'Uploaded on', 'Downloads']
    >>> humanfriendly_releases = [
    ... ['1.23', '2015-05-25', '218'],
    ... ['1.23.1', '2015-05-26', '1354'],
    ... ['1.24', '2015-05-26', '223'],
    ... ['1.25', '2015-05-26', '4319'],
    ... ['1.25.1', '2015-06-02', '197'],
    ... ]
    >>> print(format_pretty_table(humanfriendly_releases, column_names))
    -------------------------------------
    | Version | Uploaded on | Downloads |
    -------------------------------------
    | 1.23    | 2015-05-25  |       218 |
    | 1.23.1  | 2015-05-26  |      1354 |
    | 1.24    | 2015-05-26  |       223 |
    | 1.25    | 2015-05-26  |      4319 |
    | 1.25.1  | 2015-06-02  |       197 |
    -------------------------------------

    Notes about the resulting table:

    - If a column contains numeric data (integer and/or floating point
      numbers) in all rows (ignoring column names of course) then the content
      of that column is right-aligned, as can be seen in the example above. The
      idea here is to make it easier to compare the numbers in different
      columns to each other.

    - The column names are highlighted in color so they stand out a bit more
      (see also :data:`.HIGHLIGHT_COLOR`). The following screen shot shows what
      that looks like (my terminals are always set to white text on a black
      background):

      .. image:: images/pretty-table.png
    """
    # Normalize the input because we'll have to iterate it more than once.
    data = [normalize_columns(r) for r in data]
    if column_names is not None:
        column_names = normalize_columns(column_names)
        if column_names:
            if connected_to_terminal():
                column_names = [highlight_column_name(n) for n in column_names]
            data.insert(0, column_names)
    # Calculate the maximum width of each column.
    widths = collections.defaultdict(int)
    numeric_data = collections.defaultdict(list)
    for row_index, row in enumerate(data):
        for column_index, column in enumerate(row):
            widths[column_index] = max(widths[column_index], ansi_width(column))
            if not (column_names and row_index == 0):
                numeric_data[column_index].append(bool(NUMERIC_DATA_PATTERN.match(ansi_strip(column))))
    # Create a horizontal bar of dashes as a delimiter.
    line_delimiter = horizontal_bar * (sum(widths.values()) + len(widths) * 3 + 1)
    # Start the table with a vertical bar.
    lines = [line_delimiter]
    # Format the rows and columns.
    for row_index, row in enumerate(data):
        line = [vertical_bar]
        for column_index, column in enumerate(row):
            padding = ' ' * (widths[column_index] - ansi_width(column))
            if all(numeric_data[column_index]):
                line.append(' ' + padding + column + ' ')
            else:
                line.append(' ' + column + padding + ' ')
            line.append(vertical_bar)
        lines.append(u''.join(line))
        if column_names and row_index == 0:
            lines.append(line_delimiter)
    # End the table with a vertical bar.
    lines.append(line_delimiter)
    # Join the lines, returning a single string.
    return u'\n'.join(lines)


def format_robust_table(data, column_names):
    """
    Render tabular data with one column per line (allowing columns with line breaks).

    :param data: An iterable (e.g. a :func:`tuple` or :class:`list`)
                 containing the rows of the table, where each row is an
                 iterable containing the columns of the table (strings).
    :param column_names: An iterable of column names (strings).
    :returns: The rendered table (a string).

    Here's an example:

    >>> from humanfriendly.tables import format_robust_table
    >>> column_names = ['Version', 'Uploaded on', 'Downloads']
    >>> humanfriendly_releases = [
    ... ['1.23', '2015-05-25', '218'],
    ... ['1.23.1', '2015-05-26', '1354'],
    ... ['1.24', '2015-05-26', '223'],
    ... ['1.25', '2015-05-26', '4319'],
    ... ['1.25.1', '2015-06-02', '197'],
    ... ]
    >>> print(format_robust_table(humanfriendly_releases, column_names))
    -----------------------
    Version: 1.23
    Uploaded on: 2015-05-25
    Downloads: 218
    -----------------------
    Version: 1.23.1
    Uploaded on: 2015-05-26
    Downloads: 1354
    -----------------------
    Version: 1.24
    Uploaded on: 2015-05-26
    Downloads: 223
    -----------------------
    Version: 1.25
    Uploaded on: 2015-05-26
    Downloads: 4319
    -----------------------
    Version: 1.25.1
    Uploaded on: 2015-06-02
    Downloads: 197
    -----------------------

    The column names are highlighted in bold font and color so they stand out a
    bit more (see :data:`.HIGHLIGHT_COLOR`).
    """
    blocks = []
    column_names = ["%s:" % n for n in normalize_columns(column_names)]
    if connected_to_terminal():
        column_names = [highlight_column_name(n) for n in column_names]
    # Convert each row into one or more `name: value' lines (one per column)
    # and group each `row of lines' into a block (i.e. rows become blocks).
    for row in data:
        lines = []
        for column_index, column_text in enumerate(normalize_columns(row)):
            stripped_column = column_text.strip()
            if '\n' not in stripped_column:
                # Columns without line breaks are formatted inline.
                lines.append("%s %s" % (column_names[column_index], stripped_column))
            else:
                # Columns with line breaks could very well contain indented
                # lines, so we'll put the column name on a separate line. This
                # way any indentation remains intact, and it's easier to
                # copy/paste the text.
                lines.append(column_names[column_index])
                lines.extend(column_text.rstrip().splitlines())
        blocks.append(lines)
    # Calculate the width of the row delimiter.
    num_rows, num_columns = find_terminal_size()
    longest_line = max(max(map(ansi_width, lines)) for lines in blocks)
    delimiter = u"\n%s\n" % ('-' * min(longest_line, num_columns))
    # Force a delimiter at the start and end of the table.
    blocks.insert(0, "")
    blocks.append("")
    # Embed the row delimiter between every two blocks.
    return delimiter.join(u"\n".join(b) for b in blocks).strip()


def normalize_columns(row):
    return [unicode_type(c) for c in row]


def highlight_column_name(name):
    return ansi_wrap(name, bold=True, color=HIGHLIGHT_COLOR)