#!/usr/bin/env python
# cardinal_pythonlib/rnc_text.py

"""
===============================================================================

    Original code copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of cardinal_pythonlib.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

===============================================================================

**Low-quality functions relating to textfile results storage/analysis.**

"""

import csv
import datetime
import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence, TextIO, Tuple

log = logging.getLogger(__name__)


def produce_csv_output(filehandle: TextIO,
                       fields: Sequence[str],
                       values: Iterable[str]) -> None:
    """
    Produce CSV output, without using ``csv.writer``, so the log can be used
    for lots of things.

    - ... eh? What was I talking about?
    - POOR; DEPRECATED.

    Args:
        filehandle: file to write to
        fields: field names
        values: values
    """
    output_csv(filehandle, fields)
    for row in values:
        output_csv(filehandle, row)


def output_csv(filehandle: TextIO, values: Iterable[str]) -> None:
    """
    Write a line of CSV. POOR; does not escape things properly. DEPRECATED.

    Args:
        filehandle: file to write to
        values: values
    """
    line = ",".join(values)
    filehandle.write(line + "\n")


def get_what_follows_raw(s: str,
                         prefix: str,
                         onlyatstart: bool = True,
                         stripwhitespace: bool = True) -> Tuple[bool, str]:
    """
    Find the part of ``s`` that is after ``prefix``.

    Args:
        s: string to analyse
        prefix: prefix to find
        onlyatstart: only accept the prefix if it is right at the start of
            ``s``
        stripwhitespace: remove whitespace from the result

    Returns:
        tuple: ``(found, result)``

    """
    prefixstart = s.find(prefix)
    if ((prefixstart == 0 and onlyatstart) or
            (prefixstart != -1 and not onlyatstart)):
        # substring found
        resultstart = prefixstart + len(prefix)
        result = s[resultstart:]
        if stripwhitespace:
            result = result.strip()
        return True, result
    return False, ""


def get_what_follows(strings: Sequence[str],
                     prefix: str,
                     onlyatstart: bool = True,
                     stripwhitespace: bool = True,
                     precedingline: str = "") -> str:
    """
    Find a string in ``strings`` that begins with ``prefix``; return the part
    that's after ``prefix``. Optionally, require that the preceding string
    (line) is ``precedingline``.

    Args:
        strings: strings to analyse
        prefix: prefix to find
        onlyatstart: only accept the prefix if it is right at the start of
            ``s``
        stripwhitespace: remove whitespace from the result
        precedingline: if truthy, require that the preceding line be as
            specified here

    Returns:
        the line fragment

    """
    if not precedingline:
        for s in strings:
            (found, result) = get_what_follows_raw(s, prefix, onlyatstart,
                                                   stripwhitespace)
            if found:
                return result
        return ""
    else:
        for i in range(1, len(strings)):  # i indexes the second of a pair
            if strings[i-1].find(precedingline) == 0:
                # ... if found at the start
                (found, result) = get_what_follows_raw(strings[i], prefix,
                                                       onlyatstart,
                                                       stripwhitespace)
                if found:
                    return result
        return ""


def get_string(strings: Sequence[str],
               prefix: str,
               ignoreleadingcolon: bool = False,
               precedingline: str = "") -> Optional[str]:
    """
    Find a string as per :func:`get_what_follows`.

    Args:
        strings: see :func:`get_what_follows`
        prefix: see :func:`get_what_follows`
        ignoreleadingcolon: if ``True``, restrict the result to what comes
            after its first colon (and whitespace-strip that)
        precedingline: see :func:`get_what_follows`

    Returns:
        the line fragment

    """
    s = get_what_follows(strings, prefix, precedingline=precedingline)
    if ignoreleadingcolon:
        f = s.find(":")
        if f != -1:
            s = s[f+1:].strip()
    if len(s) == 0:
        return None
    return s


def get_string_relative(strings: Sequence[str],
                        prefix1: str,
                        delta: int,
                        prefix2: str,
                        ignoreleadingcolon: bool = False,
                        stripwhitespace: bool = True) -> Optional[str]:
    """
    Finds a line (string) in ``strings`` beginning with ``prefix1``. Moves
    ``delta`` lines (strings) further. Returns the end of the line that
    begins with ``prefix2``, if found.

    Args:
        strings: as above
        prefix1: as above
        delta: as above
        prefix2: as above
        ignoreleadingcolon: restrict the result to the part after its first
            colon?
        stripwhitespace: strip whitespace from the start/end of the result?

    Returns:
        the line fragment
    """
    for firstline in range(0, len(strings)):
        if strings[firstline].find(prefix1) == 0:  # if found...
            secondline = firstline + delta
            if secondline < 0 or secondline >= len(strings):
                continue
            if strings[secondline].find(prefix2) == 0:
                s = strings[secondline][len(prefix2):]
                if stripwhitespace:
                    s = s.strip()
                if ignoreleadingcolon:
                    f = s.find(":")
                    if f != -1:
                        s = s[f+1:].strip()
                    if stripwhitespace:
                        s = s.strip()
                if len(s) == 0:
                    return None
                return s
    return None


def get_int(strings: Sequence[str],
            prefix: str,
            ignoreleadingcolon: bool = False,
            precedingline: str = "") -> Optional[int]:
    """
    Fetches an integer parameter via :func:`get_string`.
    """
    return get_int_raw(get_string(strings, prefix,
                                  ignoreleadingcolon=ignoreleadingcolon,
                                  precedingline=precedingline))


def get_float(strings: Sequence[str],
              prefix: str,
              ignoreleadingcolon: bool = False,
              precedingline: str = "") -> Optional[float]:
    """
    Fetches a float parameter via :func:`get_string`.
    """
    return get_float_raw(get_string(strings, prefix,
                                    ignoreleadingcolon=ignoreleadingcolon,
                                    precedingline=precedingline))


def get_int_raw(s: str) -> Optional[int]:
    """
    Converts its input to an int.

    Args:
        s: string

    Returns:
        ``int(s)``, or ``None`` if ``s`` is ``None``

    Raises:
        ValueError: if it's a bad string

    """
    if s is None:
        return None
    return int(s)


def get_bool_raw(s: str) -> Optional[bool]:
    """
    Maps ``"Y"``, ``"y"`` to ``True`` and ``"N"``, ``"n"`` to ``False``.
    """
    if s == "Y" or s == "y":
        return True
    elif s == "N" or s == "n":
        return False
    return None


def get_float_raw(s: str) -> Optional[float]:
    """
    Converts its input to a float.

    Args:
        s: string

    Returns:
        ``int(s)``, or ``None`` if ``s`` is ``None``

    Raises:
        ValueError: if it's a bad string

    """
    if s is None:
        return None
    return float(s)


def get_bool(strings: Sequence[str],
             prefix: str,
             ignoreleadingcolon: bool = False,
             precedingline: str = "") -> Optional[bool]:
    """
    Fetches a boolean parameter via :func:`get_string`.
    """
    return get_bool_raw(get_string(strings, prefix,
                                   ignoreleadingcolon=ignoreleadingcolon,
                                   precedingline=precedingline))


def get_bool_relative(strings: Sequence[str],
                      prefix1: str,
                      delta: int,
                      prefix2: str,
                      ignoreleadingcolon: bool = False) -> Optional[bool]:
    """
    Fetches a boolean parameter via :func:`get_string_relative`.
    """
    return get_bool_raw(get_string_relative(
        strings, prefix1, delta, prefix2,
        ignoreleadingcolon=ignoreleadingcolon))


def get_float_relative(strings: Sequence[str],
                       prefix1: str,
                       delta: int,
                       prefix2: str,
                       ignoreleadingcolon: bool = False) -> Optional[float]:
    """
    Fetches a float parameter via :func:`get_string_relative`.
    """
    return get_float_raw(get_string_relative(
        strings, prefix1, delta, prefix2,
        ignoreleadingcolon=ignoreleadingcolon))


def get_int_relative(strings: Sequence[str],
                     prefix1: str,
                     delta: int,
                     prefix2: str,
                     ignoreleadingcolon: bool = False) -> Optional[int]:
    """
    Fetches an int parameter via :func:`get_string_relative`.
    """
    return get_int_raw(get_string_relative(
        strings, prefix1, delta, prefix2,
        ignoreleadingcolon=ignoreleadingcolon))


def get_datetime(strings: Sequence[str],
                 prefix: str,
                 datetime_format_string: str,
                 ignoreleadingcolon: bool = False,
                 precedingline: str = "") -> Optional[datetime.datetime]:
    """
    Fetches a ``datetime.datetime`` parameter via :func:`get_string`.
    """
    x = get_string(strings, prefix, ignoreleadingcolon=ignoreleadingcolon,
                   precedingline=precedingline)
    if len(x) == 0:
        return None
    # For the format strings you can pass to datetime.datetime.strptime, see
    # http://docs.python.org/library/datetime.html
    # A typical one is "%d-%b-%Y (%H:%M:%S)"
    d = datetime.datetime.strptime(x, datetime_format_string)
    return d


def find_line_beginning(strings: Sequence[str],
                        linestart: Optional[str]) -> int:
    """
    Finds the index of the line in ``strings`` that begins with ``linestart``,
    or ``-1`` if none is found.

    If ``linestart is None``, match an empty line.
    """
    if linestart is None:  # match an empty line
        for i in range(len(strings)):
            if is_empty_string(strings[i]):
                return i
        return -1
    for i in range(len(strings)):
        if strings[i].find(linestart) == 0:
            return i
    return -1


def find_line_containing(strings: Sequence[str], contents: str) -> int:
    """
    Finds the index of the line in ``strings`` that contains ``contents``,
    or ``-1`` if none is found.
    """
    for i in range(len(strings)):
        if strings[i].find(contents) != -1:
            return i
    return -1


def get_lines_from_to(strings: List[str],
                      firstlinestart: str,
                      list_of_lastline_starts: Iterable[Optional[str]]) \
        -> List[str]:
    """
    Takes a list of ``strings``. Returns a list of strings FROM
    ``firstlinestart`` (inclusive) TO the first of ``list_of_lastline_starts``
    (exclusive).

    To search to the end of the list, use ``list_of_lastline_starts = []``.

    To search to a blank line, use ``list_of_lastline_starts = [None]``
    """
    start_index = find_line_beginning(strings, firstlinestart)
    # log.debug("start_index: {}".format(start_index))
    if start_index == -1:
        return []
    end_offset = None  # itself a valid slice index
    for lls in list_of_lastline_starts:
        possible_end_offset = find_line_beginning(strings[start_index:], lls)
        # log.debug("lls {!r} -> possible_end_offset {}".format(
        #     lls, possible_end_offset))
        if possible_end_offset != -1:  # found one
            if end_offset is None or possible_end_offset < end_offset:
                end_offset = possible_end_offset
    end_index = None if end_offset is None else (start_index + end_offset)
    # log.debug("end_index: {}".format(end_index))
    return strings[start_index:end_index]


def is_empty_string(s: str) -> bool:
    """
    Is the string empty (ignoring whitespace)?
    """
    return len(s.strip()) == 0


def csv_to_list_of_fields(lines: List[str],
                          csvheader: str,
                          quotechar: str = '"') -> List[str]:
    """
    Extracts data from a list of CSV lines (starting with a defined header
    line) embedded in a longer text block but ending with a blank line.
    
    Used for processing e.g. MonkeyCantab rescue text output.

    Args:
        lines: CSV lines
        csvheader: CSV header line
        quotechar: ``quotechar`` parameter passed to :func:`csv.reader`

    Returns:
        list (by row) of lists (by value); see example

    Test code:

    .. code-block:: python

        import logging
        from cardinal_pythonlib.rnc_text import *
        logging.basicConfig(level=logging.DEBUG)
        
        myheader = "field1,field2,field3"
        mycsvlines = [
            "irrelevant line",
            myheader,  # header: START
            "row1value1,row1value2,row1value3",
            "row2value1,row2value2,row2value3",
            "",  # terminating blank line: END
            "other irrelevant line",
        ]
        csv_to_list_of_fields(mycsvlines, myheader)
        # [['row1value1', 'row1value2', 'row1value3'], ['row2value1', 'row2value2', 'row2value3']]

    """  # noqa
    data = []  # type: List[str]
    # an empty line marks the end of the block
    csvlines = get_lines_from_to(lines, csvheader, [None])[1:]
    # ... remove the CSV header
    reader = csv.reader(csvlines, quotechar=quotechar)
    for fields in reader:
        data.append(fields)
    return data


def csv_to_list_of_dicts(lines: List[str],
                         csvheader: str,
                         quotechar: str = '"') -> List[Dict[str, str]]:
    """
    Extracts data from a list of CSV lines (starting with a defined header
    line) embedded in a longer text block but ending with a blank line.

    Args:
        lines: CSV lines
        csvheader: CSV header line
        quotechar: ``quotechar`` parameter passed to :func:`csv.reader`

    Returns:
        list of dictionaries mapping fieldnames (from the header) to values

    """
    data = []  # type: List[Dict[str, str]]
    # an empty line marks the end of the block
    csvlines = get_lines_from_to(lines, csvheader, [None])[1:]
    # ... remove the CSV header
    headerfields = csvheader.split(",")
    reader = csv.reader(csvlines, quotechar=quotechar)
    for fields in reader:
        row = {}  # type: Dict[str, str]
        for f in range(len(headerfields)):
            row[headerfields[f]] = fields[f]
        data.append(row)
    return data


def dictlist_convert_to_string(dict_list: Iterable[Dict], key: str) -> None:
    """
    Process an iterable of dictionaries. For each dictionary ``d``, convert
    (in place) ``d[key]`` to a string form, ``str(d[key])``. If the result is a
    blank string, convert it to ``None``.
    """
    for d in dict_list:
        d[key] = str(d[key])
        if d[key] == "":
            d[key] = None


def dictlist_convert_to_datetime(dict_list: Iterable[Dict],
                                 key: str,
                                 datetime_format_string: str) -> None:
    """
    Process an iterable of dictionaries. For each dictionary ``d``, convert
    (in place) ``d[key]`` to a ``datetime.datetime`` form, using
    ``datetime_format_string`` as the format parameter to
    :func:`datetime.datetime.strptime`.
    """
    for d in dict_list:
        d[key] = datetime.datetime.strptime(d[key], datetime_format_string)


def dictlist_convert_to_int(dict_list: Iterable[Dict], key: str) -> None:
    """
    Process an iterable of dictionaries. For each dictionary ``d``, convert
    (in place) ``d[key]`` to an integer. If that fails, convert it to ``None``.
    """
    for d in dict_list:
        try:
            d[key] = int(d[key])
        except ValueError:
            d[key] = None


def dictlist_convert_to_float(dict_list: Iterable[Dict], key: str) -> None:
    """
    Process an iterable of dictionaries. For each dictionary ``d``, convert
    (in place) ``d[key]`` to a float. If that fails, convert it to ``None``.
    """
    for d in dict_list:
        try:
            d[key] = float(d[key])
        except ValueError:
            d[key] = None


def dictlist_convert_to_bool(dict_list: Iterable[Dict], key: str) -> None:
    """
    Process an iterable of dictionaries. For each dictionary ``d``, convert
    (in place) ``d[key]`` to a bool. If that fails, convert it to ``None``.
    """
    for d in dict_list:
        # d[key] = True if d[key] == "Y" else False
        d[key] = 1 if d[key] == "Y" else 0


def dictlist_replace(dict_list: Iterable[Dict], key: str, value: Any) -> None:
    """
    Process an iterable of dictionaries. For each dictionary ``d``, change
    (in place) ``d[key]`` to ``value``.
    """
    for d in dict_list:
        d[key] = value


def dictlist_wipe_key(dict_list: Iterable[Dict], key: str) -> None:
    """
    Process an iterable of dictionaries. For each dictionary ``d``, delete
    ``d[key]`` if it exists.
    """
    for d in dict_list:
        d.pop(key, None)
