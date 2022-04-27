#!/usr/bin/env python
# cardinal_pythonlib/datamapping.py

"""
===============================================================================

    Original code copyright (C) 2009-2022 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of cardinal_pythonlib.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        https://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

===============================================================================

**Functions to help transform data.**

"""

from typing import Any, Dict, Iterable, List, Tuple


# =============================================================================
# Mapping
# =============================================================================


def map_value(
    value: Any,
    maplist: Iterable[Tuple[Iterable[Any], Any]],
    transmit_none: bool = True,
    required: bool = True,
    default: Any = None,
    name: str = None,
) -> Any:
    """
    1. If the value is ``None`` and ``transmit_none`` is true, return ``None``.

    2. Map ``value`` to a result, via ``mapping``, which is a list of tuples
       ``possibilities, result``. Work through ``maplist`` in sequence, and if
       ``value`` is in ``possibilities``, return result.

    3. If no result was found, then:

       - if ``required`` is False, return ``default``;
       - otherwise, raise :exc:`ValueError`, using ``name`` to describe the
         problem.
    """
    if value is None and transmit_none:
        return None
    for possibilities, result in maplist:
        if value in possibilities:
            return result
    # Not found.
    if required:
        identity = f" for {name}" if name else ""
        msg = f"Bad value{identity}: {value!r}"
        raise ValueError(msg)
    else:
        return default


def dict_to_map(d: Dict[Any, Any]) -> List[Tuple[List[Any], Any]]:
    """
    Converts a dictionary into a structure usable by :func:`map_value`.
    """
    return [([k], v) for k, v in d.items()]
