#!/usr/bin/env python
# cardinal_pythonlib/psychiatry/mk_r_druglists.py

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

**Make an R script including constants for drugs.**

"""

# =============================================================================
# Imports
# =============================================================================

from datetime import datetime
from typing import List

from cardinal_pythonlib.psychiatry.drugs import (
    all_drugs_where,
    Drug,
    get_drug,
)


# =============================================================================
# Constants
# =============================================================================

R_SHEBANG_LINE = "#!/usr/bin/env Rscript"


# =============================================================================
# Script generation
# =============================================================================


def r_string_literal(x: str) -> str:
    r"""
    Creates an R string literal.

    - Escape backslashes, \ -> \\
    - Escape double quotes, " -> \"
    - Surround in double quotes.
    """
    single_backslash = "\\"
    double_backslash = "\\\\"
    dquote = '"'
    escaped_dquote = '\\"'
    return (
        dquote
        + x.replace(single_backslash, double_backslash).replace(
            dquote, escaped_dquote
        )
        + dquote
    )


def drugs_to_regex(drugs: List[Drug]) -> str:
    """
    Convert a list of drugs to a single regex.
    """
    return r_string_literal("|".join(d.regex_text() for d in drugs))


def rscript() -> str:
    """
    Generates the R script containing constants of interest.
    """
    converter = drugs_to_regex  # drugs_to_rvec

    now = datetime.now()

    # https://www.nhs.uk/mental-health/talking-therapies-medicine-treatments/medicines-and-psychiatry/antidepressants/overview/  # noqa
    ssri = converter(all_drugs_where(ssri=True, mixture=False))
    snri = converter(all_drugs_where(snri=True, mixture=False))
    mirtazapine = converter([get_drug("mirtazapine")])
    tca = converter(all_drugs_where(tricyclic=True, mixture=False))
    trazodone = converter([get_drug("trazodone")])
    maoi = converter(
        all_drugs_where(monoamine_oxidase_inhibitor=True, mixture=False)
    )

    nice_antidepressant_augmentation_antipsychotics = converter(
        [
            get_drug("aripiprazole"),
            get_drug("risperidone"),
            get_drug("olanzapine"),
            get_drug("quetiapine"),
        ]
    )
    flupentixol = converter([get_drug("flupentixol")])

    lithium = converter([get_drug("lithium")])
    lamotrigine = converter([get_drug("lamotrigine")])

    triiodothyronine = converter([get_drug("triiodothyronine")])  # T3

    return f"""{R_SHEBANG_LINE}

# R script with constants for drug names, including brand names and regular
# expressions for common but unambiguous mis-spellings.
#
# Generated by cardinal_pythonlib/psychiatry/mk_r_druglists.py at {now}
#
# Typical use:
#
#   if (!require("pacman")) install.packages("pacman")
#   pacman::p_load(tidyverse)  # for plyr, stringr
#   mydata <- tibble(drug = c("fluoxetine", "prozac", "citalopram", "insulin"))
#   mydata <- (
#       mydata
#       %>% mutate(
#           ssri = str_detect(drug, regex(SSRI, ignore_case = TRUE))
#           # etc.
#       )
#  )

SSRI <- {ssri}

SNRI <- {snri}

MIRTAZAPINE <- {mirtazapine}

TCA <- {tca}

TRAZODONE <- {trazodone}

MAOI <- {maoi}

NICE_ANTIDEPRESSANT_AUGMENTATION_ANTIPSYCHOTICS <- {nice_antidepressant_augmentation_antipsychotics}

FLUPENTIXOL <- {flupentixol}

LITHIUM <- {lithium}

LAMOTRIGINE <- {lamotrigine}

TRIIODOTHYRONINE <- {triiodothyronine}

"""  # noqa


# =============================================================================
# Command-line entry point
# =============================================================================


def main() -> None:
    print(rscript())


if __name__ == "__main__":
    main()
