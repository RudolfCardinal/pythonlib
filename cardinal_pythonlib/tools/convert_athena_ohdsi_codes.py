#!/usr/bin/env python
# cardinal_pythonlib/tools/convert_athena_ohdsi_codes.py

r"""
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

Convert SNOMED-CT codes, and their children, to OPCS4 procedure codes, given
an appropriate SNOMED-and-OPCS download from Athena OHDSI; see See
https://athena.ohdsi.org/. More generally, does this for any pair of
vocabularies.

Example:

.. code-block:: bash

    cardinalpythonlib_convert_athena_ohdsi_codes 175898006 118677009 265764009 --src_vocabulary SNOMED --descendants --dest_vocabulary OPCS4 > renal_procedures_opcs4.txt
    # ... kidney operation, procedure on urinary system, renal dialysis

"""  # noqa

import argparse
import logging
import os
from typing import Iterable, List, Set

from cardinal_pythonlib.athena_ohdsi import (
    AthenaConceptRow,
    AthenaRelationshipId,
    AthenaVocabularyId,
    get_athena_concepts,
    get_athena_concept_relationships,
)
from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger

log = logging.getLogger()

DEFAULT_CONCEPT = os.path.join(os.getcwd(), "CONCEPT.csv")
DEFAULT_CONCEPT_RELATIONSHIP = os.path.join(os.getcwd(),
                                            "CONCEPT_RELATIONSHIP.csv")


def report(concepts: Iterable[AthenaConceptRow]) -> str:
    descriptions = [str(c) for c in concepts]
    return "\n".join(sorted(descriptions))


def print_equivalent_opcs_codes(source_vocabulary: str,
                                source_codes: List[int],
                                destination_vocabulary: str,
                                concept_file: str,
                                concept_relationship_file: str,
                                with_descendants: bool = False) -> None:
    """
    Print codes from another vocabulary equivalent to the supplied source
    codes and (optionally) their descendants.

    Args:
        source_vocabulary:
            source vocabulary, e.g. ``SNOMED``
        source_codes:
            list of source (e.g. SNOMED-CT) codes to use
        destination_vocabulary:
            destination vocabulary
        concept_file:
            Athena OHDSI CONCEPT.csv TSV file, containing both vocabularies
        concept_relationship_file:
            Athena OHDSI CONCEPT_RELATIONSHIP.csv TSV file, containing both
            vocabularies
        with_descendants:
            include all descendants of the codes specified?
    """
    if not source_codes:
        log.error("No starting codes.")
        return
    log.debug(f"Starting with source codes: {source_codes!r}")
    log.debug(f"Concepts file: {concept_file}")
    log.debug(f"Concept relationship file: {concept_relationship_file}")

    equivalent_relationships = [
        AthenaRelationshipId.IS_A
    ]
    child_parent_relationships = [
        AthenaRelationshipId.MAPS_TO,
        AthenaRelationshipId.MAPPED_FROM,
        AthenaRelationshipId.SUBSUMES,
    ]
    all_relationships_of_interest = (
        equivalent_relationships +
        child_parent_relationships
    )

    # Since we are scanning many times, cache what we care about:

    concept_rows = get_athena_concepts(
        tsv_filename=concept_file,
        vocabulary_ids=[source_vocabulary, destination_vocabulary],
    )
    cr_rows = get_athena_concept_relationships(
        tsv_filename=concept_relationship_file,
        relationship_id_values=all_relationships_of_interest
    )

    # 1. Find Athena concepts from source codes
    source_codes_str = [str(x) for x in source_codes]
    parent_concepts = get_athena_concepts(
        cached_concepts=concept_rows,
        vocabulary_ids=[source_vocabulary],
        concept_codes=source_codes_str,
    )
    log.info(f"Athena concepts for starting source codes:\n"
             f"{report(parent_concepts)}")

    # 2. Find children
    source_concept_ids = set(p.concept_id for p in parent_concepts)
    if with_descendants:
        parents_to_search = source_concept_ids
        # noinspection PyTypeChecker
        ignore = set()  # type: Set[int]
        while True:
            log.debug("Iterating to find children...")
            # log.debug(f"parents_to_search = {parents_to_search}")
            # log.debug(f"ignore = {ignore}")
            new_children = [
                relrow.concept_id_1
                for relrow in get_athena_concept_relationships(
                    cached_concept_relationships=cr_rows,
                    relationship_id_values=equivalent_relationships,
                    concept_id_2_values=parents_to_search,
                    not_concept_id_1_values=ignore
                )
            ]
            if not new_children:
                break
            ignore.update(parents_to_search)  # don't search these twice
            parents_to_search = new_children
            source_concept_ids.update(new_children)
            log.debug(f"Currently have {len(source_concept_ids)} "
                      f"source concepts")
            # log.debug(f"... {source_concept_ids}")

    # Cosmetic only...
    source_concepts = get_athena_concepts(
        cached_concepts=concept_rows,
        concept_ids=source_concept_ids
    )
    log.debug(f"All source concepts:\n"
              f"{report(source_concepts)}")
    log.debug(f"source_concept_ids = {source_concept_ids}")

    # 3. Find equivalent concepts in the destination vocabulary
    destination_concept_ids = set(
        relrow.concept_id_2
        for relrow in get_athena_concept_relationships(
            cached_concept_relationships=cr_rows,
            concept_id_1_values=source_concept_ids,
            relationship_id_values=child_parent_relationships
        )
    ) - source_concept_ids
    # There are plenty of codes that are listed as mapping to themselves; we
    # ignore those (by subtracting descendant_concept_ids).
    log.debug(f"Athena concepts for equivalents: {destination_concept_ids!r}")
    if not destination_concept_ids:
        log.error("No equivalents.")
        return

    # 4. Find the actual OPCS codes
    dest_rows = sorted(
        get_athena_concepts(
            tsv_filename=concept_file,
            vocabulary_ids=[destination_vocabulary],
            concept_ids=destination_concept_ids,
        ),
        key=lambda cr: cr.concept_code
    )
    log.info(f"Destination ({destination_vocabulary}) equivalents follow.")
    for r in dest_rows:
        print(r)


def main() -> None:
    """
    Command-line entry point.
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "source_codes", nargs="+", type=int,
        help="Source codes to look up "
             "(along with their descendants if --descendants is specified)"
    )
    parser.add_argument(
        "--descendants", action="store_true",
        help="Include descendants of the codes specified"
    )
    parser.add_argument(
        "--concept", type=str, default=DEFAULT_CONCEPT,
        help="Athena OHDSI CONCEPT.csv TSV file including the source and "
             "destination vocabularies"
    )
    parser.add_argument(
        "--concept_relationship", type=str,
        default=DEFAULT_CONCEPT_RELATIONSHIP,
        help="Athena OHDSI CONCEPT_RELATIONSHIP.csv TSV file "
             "including the source and destination vocabularies"
    )
    parser.add_argument(
        "--src_vocabulary", type=str, default=AthenaVocabularyId.SNOMED,
        help="Source vocabulary"
    )
    parser.add_argument(
        "--dest_vocabulary", type=str, default=AthenaVocabularyId.OPCS4,
        help="Destination vocabulary"
    )
    args = parser.parse_args()
    main_only_quicksetup_rootlogger()
    print_equivalent_opcs_codes(
        source_codes=args.source_codes,
        source_vocabulary=args.src_vocabulary,
        destination_vocabulary=args.dest_vocabulary,
        concept_file=args.concept,
        concept_relationship_file=args.concept_relationship,
        with_descendants=args.descendants,
    )


if __name__ == "__main__":
    main()
