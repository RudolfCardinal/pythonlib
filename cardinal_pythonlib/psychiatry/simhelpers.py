#!/usr/bin/env python
# cardinal_pythonlib/psychiatry/simhelpers.py

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

**Helper functions for simulating behaviour.**

"""

# =============================================================================
# Imports
# =============================================================================

import logging
from typing import Any, Dict, List, Iterable, Sequence, Set, Tuple, Union

from cardinal_pythonlib.dicts import HashableDict

log = logging.getLogger(__name__)


# =============================================================================
# Parameter recovery
# =============================================================================


def _central_value(values: Union[List, Tuple], name: str = "?") -> Any:
    """
    Returns the central value of a list/tuple. Raises :exc:`ValueError` if
    ``values`` is not a list/tuple or is empty.

    If there is an even number of values, reports a warning to the log and
    returns the value immediately preceding the "virtual" centre. Thus, if
    there are five values, the third will be returned; if there are four
    values, the second will be returned (with a warning).

    The ``name`` parameter is cosmetic and is only used to annotate
    errors/warnings.
    """
    if not isinstance(values, (list, tuple)):
        raise ValueError(
            f"Parameter {name!r} should have been list/tuple but was "
            f"{values!r}"
        )
    n = len(values)
    if n == 0:
        raise ValueError(f"Parameter {name!r} has empty values")
    if n % 2 == 0:
        log.warning(
            f"Parameter {name!r} has an even number of values, so no centre"
        )
    # For odd n, the midpoint is n // 2. But to cope with even n as well:
    # n     index range     want index  n // 2      (n + 1) // 2
    # 1     0-0             0           0           1
    # 2     0-1             0           1           1
    # 3     0-2             1           1           2
    # 4     0-3             1           2           2
    # 5     0-4             2           2           3
    # ...
    midpoint = (n + 1) // 2 - 1
    return values[midpoint]


def gen_params_around_centre(
    param_order: Sequence[str] = None,
    debug: bool = False,
    **kwargs: Union[List, Tuple],
) -> Iterable[Dict]:
    """
    OVERALL PURPOSE. Used to generate parameter combinations for a parameter
    recovery simulation (where you vary known parameters, simulate behaviour,
    and check that your analytical method recovers the known values of the
    parameters).

    STRATEGY. Parameter recovery is often computationally expensive. You might
    (for example) simulate 100 virtual subjects for each parameter combination
    (there's nothing special about that number, but e.g. after Wilson &
    Collins, 2019, PMID 31769410, Box 2/Figure 1B), because simulating a
    subject that chooses based on calculated probabilities introduces random
    noise. You will want to simulate a range of parameter combinations.

    You might want to explore the entire parameter space (in which case, see
    :func:`cardinal_pythonlib.iterhelp.product_dict`), but that may be
    computationally unfeasible -- creating the simulations takes time and
    energy, and analysing them to recover those parameters takes time and
    energy.

    An alternative strategy is to take central values of all parameters, and
    then vary one parameter at a time about those central values. For example,
    if you have n = 6 parameters with k = 5 possible values each, the
    combinatorial approach gives you k ^ n = 5 ^ 6 = 15,625 combinations --
    each requiring e.g. 100 subjects to be simulated, and parameters recovered.
    This alternative strategy gives 1 + (k - 1) * n = 1 + 4 * 6 = 25
    combinations instead. This sort of method is used in e.g. Kanen et al.
    (2019), PMID 31324936.

    Args:
        kwargs:
            Keyword arguments, whose values are sequences (lists or tuples) of
            possible parameter values for the parameter with that keyword's
            name.
        param_order:
            The default order of parameters in the resulting dictionaries is
            alphabetical. You can specify a list of strings here; any
            parameters with these names will appear in the order in which they
            appear this list, and any others will be sorted alphabetically at
            the end.
        debug:
            Report the interesting part of each combination to the log? This
            skips parameters that are always constant.

    Yields:
        Dictionaries containing one combination of possibilities (one value for
        each keyword). Unlike :func:`cardinal_pythonlib.iterhelp.product_dict`,
        the parameters vary one at a time, with the others being held at their
        central value (defined as the midpoint of the list of input values for
        that parameter, not in some numerical way). (If there is no central
        value, the one just before the centre is used, and a warning is given.)

    Examples:

    .. code-block:: python

        from cardinal_pythonlib.psychiatry.simhelpers import gen_params_around_centre
        list(gen_params_around_centre(a=[1, 2, 3], b=[4, 5, 6], c=[7, 8, 9], d=[10]))
    """  # noqa
    param_order = param_order or []  # type: Sequence[str]

    def _sorter(x: str) -> Tuple[bool, Union[int, str]]:
        prespecified = x in param_order
        if prespecified:
            second = param_order.index(x)  # specified values in order
        else:
            second = x  # others sorted alphabetically
        return not prespecified, second
        # Sort order is (False, True), so we reverse ``prespecified``.

    done = set()  # type: Set[HashableDict]
    parameter_names = list(kwargs.keys())
    central_values = {
        k: _central_value(values=kwargs[k], name=k) for k in parameter_names
    }
    varying_parameters = [
        k for k in sorted(parameter_names, key=_sorter) if len(kwargs[k]) > 1
    ]
    for varying_param in varying_parameters:
        for varying_value in kwargs[varying_param]:
            combo = HashableDict(
                {
                    k: varying_value
                    if k == varying_param
                    else central_values[k]
                    for k in parameter_names
                }
            )
            if combo in done:
                continue
            if debug:
                interesting_combo = {k: combo[k] for k in varying_parameters}
                log.debug(repr(interesting_combo))
            yield combo
            done.add(combo)
