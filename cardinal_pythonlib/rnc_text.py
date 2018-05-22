#!/usr/bin/env python
# cardinal_pythonlib/rnc_text.py

"""
===============================================================================
    Copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

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

Textfile results storage.

"""

import csv
import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, TextIO, Tuple


def produce_csv_output(filehandle: TextIO,
                       fields: Sequence[str],
                       values: Iterable[str]) -> None:
    """Produce CSV output, without using csv.writer, so the log can be used for
    lots of things."""
    output_csv(filehandle, fields)
    for row in values:
        output_csv(filehandle, row)


def output_csv(filehandle: TextIO, values: Iterable[str]) -> None:
    line = ",".join(values)
    filehandle.write(line + "\n")


def get_what_follows_raw(s: str,
                         prefix: str,
                         onlyatstart: bool = True,
                         stripwhitespace: bool = True) -> Tuple[bool, str]:
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
    """Finds line beginning prefix1. Moves delta lines. Returns end of line
    beginning prefix2, if found."""
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
    return get_int_raw(get_string(strings, prefix,
                                  ignoreleadingcolon=ignoreleadingcolon,
                                  precedingline=precedingline))


def get_float(strings: Sequence[str],
              prefix: str,
              ignoreleadingcolon: bool = False,
              precedingline: str = "") -> Optional[float]:
    return get_float_raw(get_string(strings, prefix,
                                    ignoreleadingcolon=ignoreleadingcolon,
                                    precedingline=precedingline))


def get_int_raw(s: str) -> Optional[int]:
    if s is None:
        return None
    return int(s)


def get_bool_raw(s: str) -> Optional[bool]:
    if s == "Y" or s == "y":
        return True
    elif s == "N" or s == "n":
        return False
    return None


def get_float_raw(s: str) -> Optional[float]:
    if s is None:
        return None
    return float(s)


def get_bool(strings: Sequence[str],
             prefix: str,
             ignoreleadingcolon: bool = False,
             precedingline: str = "") -> Optional[bool]:
    return get_bool_raw(get_string(strings, prefix,
                                   ignoreleadingcolon=ignoreleadingcolon,
                                   precedingline=precedingline))


def get_bool_relative(strings: Sequence[str],
                      prefix1: str,
                      delta: int,
                      prefix2: str,
                      ignoreleadingcolon: bool = False) -> Optional[bool]:
    return get_bool_raw(get_string_relative(
        strings, prefix1, delta, prefix2,
        ignoreleadingcolon=ignoreleadingcolon))


def get_float_relative(strings: Sequence[str],
                       prefix1: str,
                       delta: int,
                       prefix2: str,
                       ignoreleadingcolon: bool = False) -> Optional[float]:
    return get_float_raw(get_string_relative(
        strings, prefix1, delta, prefix2,
        ignoreleadingcolon=ignoreleadingcolon))


def get_int_relative(strings: Sequence[str],
                     prefix1: str,
                     delta: int,
                     prefix2: str,
                     ignoreleadingcolon: bool = False) -> Optional[int]:
    return get_int_raw(get_string_relative(
        strings, prefix1, delta, prefix2,
        ignoreleadingcolon=ignoreleadingcolon))


def get_datetime(strings: Sequence[str],
                 prefix: str,
                 datetime_format_string: str,
                 ignoreleadingcolon: bool = False,
                 precedingline: str = "") -> Optional[datetime.datetime]:
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
    for i in range(len(strings)):
        if strings[i].find(contents) != -1:
            return i
    return -1


def get_lines_from_to(strings: List[str],
                      firstlinestart: str,
                      list_of_lastline_starts: Iterable[Optional[str]]) \
        -> List[str]:
    """Takes a list of strings. Returns a list of strings FROM firstlinestart
    (inclusive) TO one of list_of_lastline_starts (exclusive).

    To search to the end of the list, use list_of_lastline_starts = []
    To search to a blank line, use list_of_lastline_starts = [None]"""
    start_index = find_line_beginning(strings, firstlinestart)
    if start_index == -1:
        return []
    end_offset = None  # itself a valid slice index
    for lls in list_of_lastline_starts:
        possible_end_offset = find_line_beginning(strings[start_index:], lls)
        if possible_end_offset != -1:  # found one
            if end_offset is None or possible_end_offset < end_offset:
                end_offset = possible_end_offset
    end_index = None if end_offset is None else (start_index + end_offset)
    return strings[start_index:end_index]


def is_empty_string(s: str) -> bool:
    return len(s.strip(s)) == 0


def csv_to_list_of_fields(lines: List[str],
                          csvheader: str,
                          quotechar: str = '"') -> List[str]:
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
    for d in dict_list:
        d[key] = str(d[key])
        if d[key] == "":
            d[key] = None


def dictlist_convert_to_datetime(dict_list: Iterable[Dict],
                                 key: str,
                                 datetime_format_string: str) -> None:
    for d in dict_list:
        d[key] = datetime.datetime.strptime(d[key], datetime_format_string)


def dictlist_convert_to_int(dict_list: Iterable[Dict], key: str) -> None:
    for d in dict_list:
        try:
            d[key] = int(d[key])
        except ValueError:
            d[key] = None


def dictlist_convert_to_float(dict_list: Iterable[Dict], key: str) -> None:
    for d in dict_list:
        try:
            d[key] = float(d[key])
        except ValueError:
            d[key] = None


def dictlist_convert_to_bool(dict_list: Iterable[Dict], key: str) -> None:
    for d in dict_list:
        # d[key] = True if d[key] == "Y" else False
        d[key] = 1 if d[key] == "Y" else 0


def dictlist_replace(dict_list: Iterable[Dict], key: str, value: Any) -> None:
    for d in dict_list:
        d[key] = value


def dictlist_wipe_key(dict_list: Iterable[Dict], key: str) -> None:
    for d in dict_list:
        d.pop(key, None)
