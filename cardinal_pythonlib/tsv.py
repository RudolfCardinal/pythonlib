#!/usr/bin/env python
# cardinal_pythonlib/tsv.py

"""
===============================================================================

    Original code copyright (C) 2009-2020 Rudolf Cardinal (rudolf@pobox.com).

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

**Trivial functions to make tab-separated value (TSV) files.**

"""

from typing import Any, Dict, List

from cardinal_pythonlib.lists import chunks
from cardinal_pythonlib.logs import get_brace_style_log_with_null_handler
from cardinal_pythonlib.text import unescape_tabs_newlines

log = get_brace_style_log_with_null_handler(__name__)


def tsv_escape(x: Any) -> str:
    """
    Escape data for tab-separated value (TSV) format.
    """
    if x is None:
        return ""
    x = str(x)
    return x.replace("\t", "\\t").replace("\n", "\\n")


def make_tsv_row(values: List[Any]) -> str:
    """
    From a list of values, make a TSV line.
    """
    return "\t".join([tsv_escape(x) for x in values]) + "\n"


def dictlist_to_tsv(dictlist: List[Dict[str, Any]]) -> str:
    """
    From a consistent list of dictionaries mapping fieldnames to values,
    make a TSV file.
    """
    if not dictlist:
        return ""
    fieldnames = dictlist[0].keys()
    tsv = "\t".join([tsv_escape(f) for f in fieldnames]) + "\n"
    for d in dictlist:
        tsv += "\t".join([tsv_escape(v) for v in d.values()]) + "\n"
    return tsv


def tsv_pairs_to_dict(line: str, key_lower: bool = True) -> Dict[str, str]:
    r"""
    Converts a TSV line into sequential key/value pairs as a dictionary.

    For example,

    .. code-block:: none

        field1\tvalue1\tfield2\tvalue2

    becomes

    .. code-block:: none

        {"field1": "value1", "field2": "value2"}

    Args:
        line: the line
        key_lower: should the keys be forced to lower case?

    Sometimes we get lines that end in a tab. This is valid. Check with these:

    .. code-block:: python

        import logging
        from cardinal_pythonlib.tsv import tsv_pairs_to_dict
        logging.basicConfig(level=logging.DEBUG)
        print(tsv_pairs_to_dict("a\t1\tb\t2\tc\t3"))  # OK
        print(tsv_pairs_to_dict("a\t1\tb\t2\tc\t"))  # OK
        print(tsv_pairs_to_dict("a\t1\tb\t2\tc"))  # not OK; orphan 'c'
        print(tsv_pairs_to_dict("a\t1\tb\t2\tc\t\n"))  # OK

    Beware using :func:`rstrip` prior to a call to this function, because that
    will also strip trailing tabs.

    """
    items = line.split("\t")
    d = {}  # type: Dict[str, str]
    for chunk in chunks(items, 2):
        if len(chunk) < 2:
            log.warning("Bad chunk, not of length 2: {!r}", chunk)
            continue
        key = chunk[0]
        value = unescape_tabs_newlines(chunk[1])
        if key_lower:
            key = key.lower()
        d[key] = value
    return d
