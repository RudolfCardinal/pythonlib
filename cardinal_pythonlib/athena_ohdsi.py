#!/usr/bin/env python
# cardinal_pythonlib/athena_ohdsi.py

"""
===============================================================================

    Original code copyright (C) 2009-2019 Rudolf Cardinal (rudolf@pobox.com).

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

**Functions to assist with the Athena OHDSI vocabularies.**

See http://athena.ohdsi.org/.

"""

import csv
import logging
from typing import Collection, List

from cardinal_pythonlib.logs import BraceStyleAdapter
from cardinal_pythonlib.reprfunc import simple_repr
from cardinal_pythonlib.snomed import SnomedConcept

log = BraceStyleAdapter(logging.getLogger(__name__))


# =============================================================================
# Athena OHDSI mapping
# =============================================================================

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

class AthenaVocabularyId(object):
    """
    Constant-holding class for Athena vocabulary IDs that we care about.
    """
    ICD10CM = "ICD10CM"
    ICD9CM = "ICD9CM"
    OPCS4 = "OPCS4"
    SNOMED = "SNOMED"


class AthenaRelationshipId(object):
    """
    Constant-holding class for Athena relationship IDs that we care about.
    """
    IS_A = "Is a"  # "is a child of"
    MAPS_TO = "Maps to"  # converting between vocabularies
    MAPPED_FROM = "Mapped from"  # converting between vocabularies
    SUBSUMES = "Subsumes"  # "is a parent of"


# -----------------------------------------------------------------------------
# TSV row info classes
# -----------------------------------------------------------------------------

class AthenaConceptRow(object):
    """
    Simple information-holding class for ``CONCEPT.csv`` file from
    http://athena.ohdsi.org/ vocabulary download.
    """
    HEADER = [
        "concept_id", "concept_name", "domain_id", "vocabulary_id",
        "concept_class_id", "standard_concept", "concept_code",
        "valid_start_date", "valid_end_date", "invalid_reason"
    ]

    def __init__(self,
                 concept_id: str,
                 concept_name: str,
                 domain_id: str,
                 vocabulary_id: str,
                 concept_class_id: str,
                 standard_concept: str,
                 concept_code: str,
                 valid_start_date: str,
                 valid_end_date: str,
                 invalid_reason: str) -> None:
        """
        Argument order is important.

        Args:
            concept_id: Athena concept ID
            concept_name: Concept name in the originating system
            domain_id: e.g. "Observation", "Condition"
            vocabulary_id: e.g. "SNOMED", "ICD10CM"
            concept_class_id: e.g. "Substance", "3-char nonbill code"
            standard_concept: ?; e.g. "S"
            concept_code: concept code in the vocabulary (e.g. SNOMED-CT
                concept code like "3578611000001105" if vocabulary_id is
                "SNOMED"; ICD-10 code like "F32.2" if vocabulary_is is
                "ICD10CM"; etc.)
            valid_start_date: date in YYYYMMDD format
            valid_end_date: date in YYYYMMDD format
            invalid_reason: ? (but one can guess)
        """
        self.concept_id = int(concept_id)
        self.concept_name = concept_name
        self.domain_id = domain_id
        self.vocabulary_id = vocabulary_id
        self.concept_class_id = concept_class_id
        self.standard_concept = standard_concept
        self.concept_code = concept_code
        self.valid_start_date = valid_start_date
        self.valid_end_date = valid_end_date
        self.invalid_reason = invalid_reason
        # self.sort_context_concept_to_match = None

    def __repr__(self) -> str:
        return simple_repr(self, self.HEADER)

    def __str__(self) -> str:
        return (
            f"Vocabulary {self.vocabulary_id}, concept {self.concept_code} "
            f"({self.concept_name}) -> Athena concept {self.concept_id}"
        )

    # I looked at sorting them to find the best. Not wise; would need human
    # review. Just use all valid codes.

    _ = '''

    def set_sort_context_concept_to_match(self,
                                          concept: "AthenaConceptRow") -> None:
        self.sort_context_concept_to_match = concept

    def __lt__(self, other: "AthenaConceptRow") -> bool:
        """
        Compares using "less than" being equivalent to "preferable to".

        So, returns True if "self" is better than other, and False if "self" is
        worse than other; that is, all tests look like "return self is better
        than other".

        BINNED. We will use human judgement.
        """
        invalid_s = bool(self.invalid_reason)
        invalid_o = bool(other.invalid_reason)
        if invalid_s != invalid_o:
            # better not to have an "invalid" reason;
            # empty strings are "less than" full ones
            return invalid_s < invalid_o
        if self.valid_end_date != other.valid_end_date:
            # better to have a later end date
            return self.valid_end_date > other.valid_end_date
        if self.valid_start_date != other.valid_start_date:
            # better to have an earlier start date
            return self.valid_start_date < other.valid_end_date
        if self.sort_context_concept_to_match:
            # Which is closer to our target context?
            c = self.sort_context_concept_to_match
            sp = self.match_tuple(c)
            op = other.match_tuple(c)
            log.info(
                "Tie-breaking to match {c}: {s} ({sp} points) vs "
                "{o} ({op} points)",
                s=self, sp=sp, o=other, op=op, c=c
            )
            # More matching points is better
            return self.match_tuple(c) > other.match_tuple(c)
        log.warning("Tie-breaking {} and {} by ID", self, other)
        # Arbitrarily, better to have an earlier (lower) concept ID.
        return self.concept_id < other.concept_id

    def match_tuple(self, target: "AthenaConceptRow") -> Tuple[float, float]:
        """
        Returns a score reflecting our similarity to the target.

        See

        - https://stackoverflow.com/questions/8897593/similarity-between-two-text-documents
        - https://stackoverflow.com/questions/2380394/simple-implementation-of-n-gram-tf-idf-and-cosine-similarity-in-python
        - https://spacy.io/usage/vectors-similarity -- data not included
        - https://radimrehurek.com/gensim/index.html
        - https://radimrehurek.com/gensim/tut3.html
        - https://scikit-learn.org/stable/
        - http://www.nltk.org/

        BINNED. We will use human judgement.
        """  # noqa
        self_words = set(x.lower() for x in self.concept_name.split())
        other_words = set(x.lower() for x in target.concept_name.split())
        # More matching words better
        n_matching_words = len(self_words & other_words)
        # More words better (often more specific)
        n_words = len(self_words)
        return float(n_matching_words), float(n_words)

    '''

    def snomed_concept(self) -> SnomedConcept:
        """
        Assuming this Athena concept reflects a SnomedConcept, returns it.

        (Asserts if it isn't.)
        """
        assert self.vocabulary_id == AthenaVocabularyId.SNOMED
        return SnomedConcept(int(self.concept_code), self.concept_name)


class AthenaConceptRelationshipRow(object):
    """
    Simple information-holding class for ``CONCEPT_RELATIONSHIP.csv`` file from
    http://athena.ohdsi.org/ vocabulary download.
    """
    HEADER = [
        "concept_id_1", "concept_id_2", "relationship_id",
        "valid_start_date", "valid_end_date", "invalid_reason",
    ]

    def __init__(self,
                 concept_id_1: str,
                 concept_id_2: str,
                 relationship_id: str,
                 valid_start_date: str,
                 valid_end_date: str,
                 invalid_reason: str) -> None:
        """
        Argument order is important.

        Args:
            concept_id_1: Athena concept ID #1
            concept_id_2: Athena concept ID #2
            relationship_id: e.g. "Is a", "Has legal category"
            valid_start_date: date in YYYYMMDD format
            valid_end_date: date in YYYYMMDD format
            invalid_reason: ? (but one can guess)
        """
        self.concept_id_1 = int(concept_id_1)
        self.concept_id_2 = int(concept_id_2)
        self.relationship_id = relationship_id
        self.valid_start_date = valid_start_date
        self.valid_end_date = valid_end_date
        self.invalid_reason = invalid_reason

    def __repr__(self) -> str:
        return simple_repr(self, self.HEADER)

    def __str__(self) -> str:
        return (
            f"Athena concept relationship {self.concept_id_1} "
            f"{self.relationship_id!r} {self.concept_id_2}"
        )


# -----------------------------------------------------------------------------
# Fetch data from TSV files
# -----------------------------------------------------------------------------

# noinspection DuplicatedCode
def get_athena_concepts(
        tsv_filename: str,
        vocabulary_ids: Collection[str] = None,
        concept_codes: Collection[str] = None,
        concept_ids: Collection[int] = None,
        not_vocabulary_ids: Collection[str] = None,
        not_concept_codes: Collection[str] = None,
        not_concept_ids: Collection[int] = None) -> List[AthenaConceptRow]:
    """
    From the Athena ``CONCEPT.csv`` tab-separated value file, return a list
    of concepts matching the restriction criteria.

    Args:
        tsv_filename:
            filename
        vocabulary_ids:
            permissible ``vocabulary_id`` values, or None or an empty list for
            all
        concept_codes:
            permissible ``concept_code`` values, or None or an empty list for
            all
        concept_ids:
            permissible ``concept_id`` values, or None or an empty list for all
        not_vocabulary_ids:
            impermissible ``vocabulary_id`` values, or None or an empty list
            for none
        not_concept_codes:
            impermissible ``concept_code`` values, or None or an empty list for
            none
        not_concept_ids:
            impermissible ``concept_id`` values, or None or an empty list for
            none

    Returns:
        list: of :class:`AthenaConceptRow` objects

    """
    log.info("Loading Athena concepts from file: {}", tsv_filename)
    concepts = []  # type: List[AthenaConceptRow]
    n_rows_read = 0
    with open(tsv_filename, 'r') as tsvin:
        reader = csv.reader(tsvin, delimiter="\t")
        header = next(reader, None)
        if header != AthenaConceptRow.HEADER:
            raise ValueError(
                f"Athena concept file has unexpected header: {header!r}; "
                f"expected {AthenaConceptRow.HEADER!r}")
        for row in reader:
            n_rows_read += 1
            concept = AthenaConceptRow(*row)
            # Positive checks
            if vocabulary_ids and concept.vocabulary_id not in vocabulary_ids:
                continue
            if concept_codes and concept.concept_code not in concept_codes:
                continue
            if concept_ids and concept.concept_id not in concept_ids:
                continue
            # Negative checks
            if not_vocabulary_ids and concept.vocabulary_id in not_vocabulary_ids:  # noqa
                continue
            if not_concept_codes and concept.concept_code in not_concept_codes:
                continue
            if not_concept_ids and concept.concept_id in not_concept_ids:
                continue
            # log.debug("{}", concept)
            concepts.append(concept)
    log.debug("Retrieved {} concepts from {} rows", len(concepts), n_rows_read)
    return concepts


# noinspection DuplicatedCode
def get_athena_concept_relationships(
        tsv_filename: str,
        concept_id_1_values: Collection[int] = None,
        concept_id_2_values: Collection[int] = None,
        relationship_id_values: Collection[str] = None,
        not_concept_id_1_values: Collection[int] = None,
        not_concept_id_2_values: Collection[int] = None,
        not_relationship_id_values: Collection[str] = None) \
        -> List[AthenaConceptRelationshipRow]:
    """
    From the Athena ``CONCEPT_RELATIONSHIP.csv`` tab-separated value file,
    return a list of relationships matching the restriction criteria.

    Args:
        tsv_filename:
            filename
        concept_id_1_values:
            permissible ``concept_id_1`` values, or None or an empty list for
            all
        concept_id_2_values:
            permissible ``concept_id_2`` values, or None or an empty list for
            all
        relationship_id_values:
            permissible ``relationship_id`` values, or None or an empty list
            for all
        not_concept_id_1_values:
            impermissible ``concept_id_1`` values, or None or an empty list for
            none
        not_concept_id_2_values:
            impermissible ``concept_id_2`` values, or None or an empty list for
            none
        not_relationship_id_values:
            impermissible ``relationship_id`` values, or None or an empty list
            for none

    Returns:
        list: of :class:`AthenaConceptRelationshipRow` objects

    """
    log.info("Loading Athena concept relationships from file: {}",
             tsv_filename)
    relationships = []  # type: List[AthenaConceptRelationshipRow]
    n_rows_read = 0
    with open(tsv_filename, 'r') as tsvin:
        reader = csv.reader(tsvin, delimiter="\t")
        header = next(reader, None)
        if header != AthenaConceptRelationshipRow.HEADER:
            raise ValueError(
                f"Athena concept relationship file has unexpected header: "
                f"{header!r}; expected "
                f"{AthenaConceptRelationshipRow.HEADER!r}")
        for row in reader:
            n_rows_read += 1
            rel = AthenaConceptRelationshipRow(*row)
            # Positive checks
            if relationship_id_values and rel.relationship_id not in relationship_id_values:  # noqa
                continue
            if concept_id_1_values and rel.concept_id_1 not in concept_id_1_values:  # noqa
                continue
            if concept_id_2_values and rel.concept_id_2 not in concept_id_2_values:  # noqa
                continue
            # Negative checks
            if not_relationship_id_values and rel.relationship_id in not_relationship_id_values:  # noqa
                continue
            if not_concept_id_1_values and rel.concept_id_1 in not_concept_id_1_values:  # noqa
                continue
            if not_concept_id_2_values and rel.concept_id_2 in not_concept_id_2_values:  # noqa
                continue
            # log.debug("{}", rel)
            relationships.append(rel)
    log.debug("Retrieved {} relationships from {} rows",
              len(relationships), n_rows_read)
    return relationships
