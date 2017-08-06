#!/usr/bin/env python
# cardinal_pythonlib/tsv.py

"""
===============================================================================
    Copyright (C) 2009-2017 Rudolf Cardinal (rudolf@pobox.com).

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
"""

import logging
from typing import Any, Dict, List

from cardinal_pythonlib.lists import chunks
from cardinal_pythonlib.text import unescape_tabs_newlines

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def tsv_escape(x: Any) -> str:
    """
    Escape data for tab-separated value format.
    """
    if x is None:
        return ""
    x = str(x)
    return x.replace("\t", "\\t").replace("\n", "\\n")


def make_tsv_row(values: List[Any]) -> str:
    return "\t".join([tsv_escape(x) for x in values]) + "\n"


def dictlist_to_tsv(dictlist: List[Dict[str, Any]]) -> str:
    if not dictlist:
        return ""
    fieldnames = dictlist[0].keys()
    tsv = "\t".join([tsv_escape(f) for f in fieldnames]) + "\n"
    for d in dictlist:
        tsv += "\t".join([tsv_escape(v) for v in d.values()]) + "\n"
    return tsv


def tsv_pairs_to_dict(line: str, key_lower: bool = True) -> Dict[str, str]:
    """
    Converts a TSV line into sequential key/value pairs as a dictionary.
    """
    items = line.split("\t")
    d = {}  # type: Dict[str, str]
    for chunk in chunks(items, 2):
        if len(chunk) < 2:
            log.warning("Bad chunk, not of length 2: {}".format(repr(chunk)))
            continue
        key = chunk[0]
        value = unescape_tabs_newlines(chunk[1])
        if key_lower:
            key = key.lower()
        d[key] = value
    return d
