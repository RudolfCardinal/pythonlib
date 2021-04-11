#!/usr/bin/env python
# cardinal_pythonlib/json/typing_helpers.py

"""
===============================================================================

    Original code copyright (C) 2009-2021 Rudolf Cardinal (rudolf@pobox.com).

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

Type hints for JSON.

"""

from typing import Dict, List, Union

# =============================================================================
# Type definitions; see https://www.json.org/
# =============================================================================

# Types for the Python representation of JSON:
JsonLiteralType = Union[str, int, float, bool, None]
JsonValueType = Union[JsonLiteralType, Dict, List]
JsonObjectType = Dict[str, JsonValueType]
JsonArrayType = List[JsonValueType]

# Type for the string representation of JSON:
JsonAsStringType = str
