#!/usr/bin/env python
# cardinal_pythonlib/chebi.py

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

**Functions to assist with the ChEBI database.**

ChEBI: Chemical Entities of Biological Interest (ChEBI) database from
EMBL-EBI (European Molecular Biology Laboratory / European Bioinformatics
Institute).

See https://www.ebi.ac.uk/chebi/

Examples:

.. code-block:: python

    cardinalpythonlib_chebi test
    
    cardinalpythonlib_chebi search citalopram
    cardinalpythonlib_chebi search citalopram --exact_search
    cardinalpythonlib_chebi search zopiclone
    cardinalpythonlib_chebi search zopiclone --exact_search
    cardinalpythonlib_chebi search zopiclone --exact_match
    cardinalpythonlib_chebi search salicylic --inexact_search
    
    cardinalpythonlib_chebi describe citalopram simvastatin --exact_match
    
    cardinalpythonlib_chebi ancestors citalopram simvastatin

Then try this syntax:

.. code-block:: bash

    cardinalpythonlib_chebi categorize \
        --entities entities.txt \
        --entity_synonyms entity_synonyms.txt \
        --categories categories.txt \
        --category_synonyms category_synonyms.txt \
        --manual_categories manual_categories.txt \
        --results results.csv

using files like these:

.. code-block:: none

    # entities.txt
    # Things to classify.
    
    agomelatine
    aspirin
    citalopram
    simvastatin

.. code-block:: none

    # entity_synonyms.txt
    # Renaming of entities prior to lookup.
    # Find these via "cardinalpythonlib_chebi search ..." or Google with "CHEBI".
    
    aspirin, acetylsalicylic acid

.. code-block:: none

    # categories.txt
    # Categories to detect, in order of priority (high to low).
    
    serotonin reuptake inhibitor
    antidepressant

    antilipemic drug

    non-steroidal anti-inflammatory drug

.. code-block:: none

    # category_synonyms.txt
    # Categories that are equivalent but ChEBI doesn't know. 
    
    glucagon-like peptide-1 receptor agonist, hypoglycemic agent

.. code-block:: none

    # manual_categories.txt
    # Categorizations that ChEBI doesn't know. 
    
    agomelatine, antidepressant

"""  # noqa

import argparse
import csv
import logging
from typing import List, Generator, Optional, Sequence, Set, Tuple, Union

from appdirs import user_cache_dir
try:
    # noinspection PyPackageRequirements
    from libchebipy import (
        ChebiEntity,
        Relation,
        search,
        set_download_cache_path,
    )
except ImportError:
    raise ImportError("Cannot import libchebipy; try the command: pip install libChEBIpy")  # noqa

from cardinal_pythonlib.file_io import (
    gen_lines_without_comments,
    get_lines_without_comments,
)
from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger
from cardinal_pythonlib.version_string import VERSION_STRING

log = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

DEFAULT_CACHE_PATH = user_cache_dir("chebi")
DEFAULT_ANCESTOR_RELATIONSHIPS = ["has_role", "is_a"]  # both are helpful

DEFAULT_EXACT_SEARCH = False
DEFAULT_EXACT_MATCH = False


# =============================================================================
# Hashable version of ChebiEntity
# =============================================================================

_CHEBI_ID_PREFIX = "CHEBI:"


def get_chebi_id_number_str(entity: ChebiEntity) -> str:
    """
    Returns the CHEBI ID number as a string.

    Args:
        entity:
            a :class:`libchebipy.ChebiEntity`
    """
    return entity.get_id().replace(_CHEBI_ID_PREFIX, "")


def get_chebi_id_number(entity: ChebiEntity) -> int:
    """
    Returns the CHEBI ID number as an integer.

    Args:
        entity:
            a :class:`libchebipy.ChebiEntity`
    """
    return int(get_chebi_id_number_str(entity))


class HashableChebiEntity(ChebiEntity):
    """
    Hashable version of :class:`libchebipy.ChebiEntity`.
    """

    @classmethod
    def from_chebi_entity(cls, entity: ChebiEntity) -> "HashableChebiEntity":
        id_number_str = get_chebi_id_number_str(entity)
        return HashableChebiEntity(id_number_str)

    def get_id_number_str(self) -> str:
        return get_chebi_id_number_str(self)

    def get_id_number(self) -> int:
        return get_chebi_id_number(self)

    def __eq__(self, other: Union[str, int, "HashableChebiEntity"]) -> bool:
        if isinstance(other, str):
            return other == self.get_name()
        elif isinstance(other, int):
            return other == self.get_id_number()
        else:
            return self.get_id_number() == other.get_id_number()

    def __hash__(self) -> int:
        return self.get_id_number()


# =============================================================================
# Descriptions of a ChebiEntity
# =============================================================================

def brief_description(entity: ChebiEntity) -> str:
    """
    Args:
        entity:
            a :class:`ChebiEntity`

    Returns:
        str: name and ID

    """
    return f"{entity.get_name()} ({entity.get_id()})"


# =============================================================================
# Searching ChEBI
# =============================================================================

def get_entity(chebi_id: Union[int, str]) -> ChebiEntity:
    """
    Fetch a ChEBI entity by its ID.

    Args:
        chebi_id:
            integer ChEBI ID like ``15903``, or string ID like ``'15903'``,
            or string ID like ``'CHEBI:15903'``.
    """
    chebi_id = str(chebi_id)  # ignore buggy demo code; int not OK
    log.debug(f"Looking up ChEBI ID: {chebi_id}")
    return ChebiEntity(chebi_id)


def search_entities(search_term: Union[int, str],
                    exact_search: bool = DEFAULT_EXACT_SEARCH,
                    exact_match: bool = DEFAULT_EXACT_MATCH) \
        -> List[ChebiEntity]:
    """
    Search for ChEBI entities.

    Case-insensitive.

    Args:
        search_term:
            String or integer to search for.
        exact_search:
            The ``exact`` parameter to :func:`libchebipy.search`.
        exact_match:
            Ensure that the name of the result exactly matches the search term.
            Example: an exact search for "zopiclone" gives both "zopiclone
            (CHEBI:32315)" and "(5R)-zopiclone (CHEBI:53762)"; this option
            filters to the first.
    """
    log.debug(f"Searching for {search_term!r} "
              f"(exact_search={exact_search}, exact_match={exact_match})")
    results = search(search_term, exact=exact_search)
    log.debug(f"libchebipy.search({search_term!r}, exact={exact_search}) "
              f"-> {results!r}")
    if exact_match:
        if isinstance(search_term, int):
            results = [r for r in results
                       if get_chebi_id_number(r) == search_term]
        else:
            assert isinstance(search_term, str)
            results = [r for r in results
                       if r.get_name().lower() == search_term.lower()]
    log.debug(f"search_entities({search_term!r}, exact_search={exact_search}, "
              f"exact_match={exact_match}) -> {results!r}")
    return results


# =============================================================================
# Describing ChEBI entries
# =============================================================================

def describe_entity(entity: ChebiEntity) -> None:
    """
    Test function to describe a ChEBI entity.

    Args:
        entity:
            a :class:`ChebiEntity`
    """
    name = entity.get_name()

    out_lines = []  # type: List[str]
    for other in entity.get_outgoings():
        target = ChebiEntity(other.get_target_chebi_id())
        out_lines.append(
            f"    • {name} {other.get_type()} {brief_description(target)}")

    in_lines = []  # type: List[str]
    for other in entity.get_incomings():
        target = ChebiEntity(other.get_target_chebi_id())
        in_lines.append(
            f"    • {brief_description(target)} {other.get_type()} {name}")

    lines = (
        [entity.get_name(), f"  ► OUTGOING ({len(out_lines)})"] +
        out_lines +
        [f"  ► INCOMING ({len(in_lines)})"] +
        in_lines
    )
    report = "\n".join(lines)
    log.info(f"{entity.get_id()}:\n{report}")


def search_and_describe(search_term: Union[int, str],
                        exact_search: bool = DEFAULT_EXACT_SEARCH,
                        exact_match: bool = DEFAULT_EXACT_MATCH) -> None:
    """
    Search for a ChEBI term and describe it to the log.

    Args:
        search_term: search term
        exact_search: exact search?
        exact_match: exact match?
    """
    entities = search_entities(search_term, exact_search=exact_search,
                               exact_match=exact_match)
    for entity in entities:
        describe_entity(entity)


def search_and_describe_multiple(
        search_terms: List[Union[int, str]],
        exact_search: bool = DEFAULT_EXACT_SEARCH,
        exact_match: bool = DEFAULT_EXACT_MATCH) -> None:
    """
    Search for ChEBI terms; describe matching entries to the log.

    Args:
        search_terms: search term(s)
        exact_search: exact search?
        exact_match: exact match?
    """
    for search_term in search_terms:
        search_and_describe(search_term, exact_search=exact_search,
                            exact_match=exact_match)


def search_and_list(search_term: Union[int, str],
                    exact_search: bool = DEFAULT_EXACT_SEARCH,
                    exact_match: bool = DEFAULT_EXACT_MATCH) -> None:
    """
    Search for a ChEBI term; print matching entries to the log.

    Args:
        search_term: search term
        exact_search: exact search?
        exact_match: exact match?
    """
    entities = search_entities(search_term, exact_search=exact_search,
                               exact_match=exact_match)
    lines = [f"– {brief_description(entity)}" for entity in entities]
    report = "\n".join(lines)
    log.info(f"Results:\n{report}")


def search_and_list_multiple(search_terms: List[Union[int, str]],
                             exact_search: bool = DEFAULT_EXACT_SEARCH,
                             exact_match: bool = DEFAULT_EXACT_MATCH) -> None:
    """
    Search for ChEBI terms; print matching entries to the log.

    Args:
        search_terms: search term(s)
        exact_search: exact search?
        exact_match: exact match?
    """
    for search_term in search_terms:
        search_and_list(search_term, exact_search=exact_search,
                        exact_match=exact_match)


# =============================================================================
# Ancestors and descendants of ChEBI entities
# =============================================================================

def gen_ancestor_info(entity: ChebiEntity,
                      relationships: List[str] = None,
                      max_generations: int = None,
                      starting_generation_: int = 0,
                      seen_: Set[HashableChebiEntity] = None) \
        -> Generator[Tuple[HashableChebiEntity, str, int], None, None]:
    """
    Retrieves all ancestors ("outgoing" links).

    Args:
        entity:
            starting entity
        relationships:
            list of valid relationship types, e.g. "has_role"
        max_generations:
            maximum number of generations to pursue, or ``None`` for unlimited
        starting_generation_:
            for internal use only, for recursion
        seen_:
            for internal use only, for recursion

    Returns:
        list: of tuples ``entity, relationship, n_generations_above_start``
    """
    if max_generations is not None and starting_generation_ >= max_generations:
        return
    assert starting_generation_ == 0 or seen_ is not None
    seen_ = seen_ or set()  # type: Set[HashableChebiEntity]
    relationships = relationships or DEFAULT_ANCESTOR_RELATIONSHIPS
    log.debug(f"Finding ancestors of {brief_description(entity)} "
              f"(generation {starting_generation_}) "
              f"via relationships {relationships!r}")
    for rel in entity.get_outgoings():  # type: Relation
        if rel.get_type() in relationships:
            target = HashableChebiEntity(rel.get_target_chebi_id())
            log.debug(f"... found {brief_description(target)}")
            if target in seen_:
                # log.debug(f"Skipping {target!r}")
                continue
            seen_.add(target)
            yield target, rel.get_type(), starting_generation_ + 1
            yield from gen_ancestor_info(
                entity=target,
                relationships=relationships,
                starting_generation_=starting_generation_ + 1,
                seen_=seen_,
            )


def gen_ancestors(entity: ChebiEntity,
                  relationships: List[str] = None,
                  max_generations: int = None) \
        -> Generator[HashableChebiEntity, None, None]:
    """
    Generates ancestors as per :func:`gen_ancestor_info`, without relationship
    or generation info.
    """
    for (ancestor,
         relationship,
         generation) in gen_ancestor_info(entity,
                                          relationships,
                                          max_generations):
        yield ancestor


def report_ancestors(entity: ChebiEntity,
                     relationships: List[str] = None,
                     max_generations: int = None) -> None:
    """
    Fetches and reports on ancestors of an entity, e.g. via "is_a"
    relationships. See :func:`gen_ancestor_info`.
    """
    relationships = relationships or DEFAULT_ANCESTOR_RELATIONSHIPS
    ancestors = list(gen_ancestor_info(
        entity=entity,
        relationships=relationships,
        max_generations=max_generations))
    lines = [f"{entity.get_name()} ({entity.get_id()})"]
    for ancestor, relationship, generation in ancestors:
        prefix = "  " * generation
        lines.append(f"{prefix}► {relationship} "
                     f"{brief_description(ancestor)} [{generation}]")
    report = "\n".join(lines)
    log.info(f"Ancestors via {relationships!r}:\n{report}")


def report_ancestors_multiple(entity_names: List[str],
                              relationships: List[str] = None,
                              max_generations: int = None) -> None:
    """
    Looks up entities, then reports on ancestors.
    Fetches and reports on ancestors of an entity, e.g. via "is_a"
    relationships. See :func:`gen_ancestor_info`.
    """
    log.debug(f"Using ancestor relationships: {relationships!r}")
    log.debug(f"Using max_generations: {max_generations!r}")
    for entity_name in entity_names:
        for entity in search_entities(entity_name):
            report_ancestors(entity, relationships, max_generations)


# =============================================================================
# Testing
# =============================================================================

def testfunc1() -> None:
    """
    Test ChEBI interface.
    """
    log.warning("Testing: describe beta-D-glucose")
    beta_d_glucose = get_entity(15903)
    describe_entity(beta_d_glucose)
    # Cross-check:
    # https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:15903
    # ... correct.

    log.warning("Testing: describe things like 'citalopram'")
    search_and_describe("citalopram", exact_search=False)

    log.warning("Testing: show ancestors of citalopram")
    citalopram = get_entity(3723)
    report_ancestors(citalopram)
    # https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:3723

    sri = "serotonin uptake inhibitor"
    log.warning(f"Testing: search/list {sri!r}")
    search_and_list(sri)
    log.warning(f"Testing: search/describe {sri!r}")
    search_and_describe(sri)


# =============================================================================
# Mapping terms via dictionaries
# =============================================================================

class CaseInsensitiveDict(dict):
    """
    Case-insensitive dictionary for strings; see
    https://stackoverflow.com/questions/2082152/case-insensitive-dictionary
    """
    def __setitem__(self, key: str, value: str) -> None:
        # https://docs.python.org/3/reference/datamodel.html#object.__setitem__
        super().__setitem__(key.lower(), value)

    def __contains__(self, key: str) -> bool:
        # https://docs.python.org/3/reference/datamodel.html#object.__contains__
        return super().__contains__(key.lower())

    def __getitem__(self, key: str) -> str:
        # https://docs.python.org/3/reference/datamodel.html#object.__getitem__
        return super().__getitem__(key.lower())


def read_dict(filename: str) -> CaseInsensitiveDict:
    """
    Reads a filename that may have comments but is otherwise in the format

    .. code-block:: none

        a1, b1
        a2, b2
        ...

    Args:
        filename:
            filename to read

    Returns:
        dict: mapping the first column (converted to lower case) to the second
        (case left intact).

    """
    d = CaseInsensitiveDict()
    for line in gen_lines_without_comments(filename):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 2:
            a = parts[0]
            b = parts[1]
            d[a] = b
        else:
            log.error(f"Bad CSV-pair line: {line!r}")
    return d


def translate(term: str, mapping: CaseInsensitiveDict) -> Tuple[str, bool]:
    """
    Translates a term through a dictionary. If the term (once converted to
    lower case) is in the dictionary (see :func:`read_dict`), the mapped term
    is returned; otherwise the original search term is returned.

    Args:
        term:
            term to look up
        mapping:
            the mapping dictionary

    Returns:
        tuple: result (str), renamed? (bool)

    """
    result = mapping.get(term, term)
    return result, result != term


# =============================================================================
# Categorizing drugs
# =============================================================================

def get_category(entity_name: str,
                 categories: Sequence[str],
                 entity_synonyms: CaseInsensitiveDict = None,
                 category_synonyms: CaseInsensitiveDict = None,
                 manual_categories: CaseInsensitiveDict = None,
                 relationships: List[str] = None) -> Optional[str]:
    """

    Args:
        entity_name:
            name of entity to categorize
        categories:
            permissible categories (earlier preferable to later)
        entity_synonyms:
            map to rename entities
        category_synonyms:
            mapping of categories to other (preferred) categories
        manual_categories:
            manual overrides mapping entity to category
        relationships:
            list of valid relationship types defining ancestry, e.g. "has_role"

    Returns:
        chosen category, or ``None`` if none found
    """
    entity_synonyms = entity_synonyms or CaseInsensitiveDict()
    category_synonyms = category_synonyms or CaseInsensitiveDict()
    manual_categories = manual_categories or CaseInsensitiveDict()
    relationships = relationships or DEFAULT_ANCESTOR_RELATIONSHIPS

    log.debug(f"get_category: entity_name={entity_name!r}")

    # Manual override for original name?
    if entity_name in manual_categories:
        category, _ = translate(manual_categories[entity_name],
                                category_synonyms)
        log.debug(f"Manual categorization: {entity_name} → {category}")
        return category

    # Renamed?
    entity_name, renamed = translate(entity_name, entity_synonyms)

    # Manual override for renamed entity?
    if renamed:
        if entity_name in manual_categories:
            category, _ = translate(manual_categories[entity_name],
                                    category_synonyms)
            log.debug(f"Manual categorization: {entity_name} → {category}")
            return category

    # Find entity
    entities = search_entities(entity_name,
                               exact_search=True,
                               exact_match=True)
    if len(entities) == 0:
        log.warning(f"No entity found for {entity_name!r}")
        return None
    if len(entities) > 1:
        descriptions = "; ".join(brief_description(e) for e in entities)
        log.warning(f"Multiple entities found for {entity_name!r}; "
                    f"using the first. They were:\n{descriptions}")
    entity = entities[0]

    # Find category
    ancestors = list(gen_ancestors(entity, relationships=relationships))
    ancestor_categories = [
        translate(a.get_name(), category_synonyms)[0]
        for a in ancestors
    ]
    # log.debug(f"ancestor_categories: {ancestor_categories!r}")
    for category in categories:  # implements category order
        category, _ = translate(category, category_synonyms)
        if category in ancestor_categories:
            return category
    return None


def categorize_from_file(entity_filename: str,
                         category_filename: str,
                         results_filename: str,
                         entity_synonyms_filename: str = None,
                         category_synonyms_filename: str = None,
                         manual_categories_filename: str = None,
                         relationships: List[str] = None,
                         output_dialect: str = "excel",
                         headers: bool = True) -> None:
    """
    Categorizes entities.

    Args:
        entity_filename:
            input filename, one entity per line
        category_filename:
            filename containing permissible categories, one per line
            (earlier preferable to later)
        results_filename:
            output filename for CSV results
        entity_synonyms_filename
            Name of CSV file (with optional # comments) containing synonyms
            in the format ``entity_from, entity_to``.
        category_synonyms_filename:
            Name of CSV file (with optional # comments) containing synonyms
            in the format ``category_from, categoryto``.
        manual_categories_filename:
            Name of CSV file (with optional # comments) containing manual
            categorizations in the format ``entity, category``.
        relationships:
            list of valid relationship types defining ancestry, e.g. "has_role"
        output_dialect:
            CSV output dialect
        headers:
            add CSV headers?
    """
    relationships = relationships or DEFAULT_ANCESTOR_RELATIONSHIPS
    log.info(f"Using ancestor relationships {relationships!r}")

    log.info(f"Reading categories from {category_filename}")
    categories = get_lines_without_comments(category_filename)

    if entity_synonyms_filename:
        log.info(f"Reading entity synonyms from {entity_synonyms_filename}")
        entity_synonyms = read_dict(entity_synonyms_filename)
    else:
        entity_synonyms = CaseInsensitiveDict()
    log.debug(f"Using entity synonyms: {entity_synonyms!r}")

    if category_synonyms_filename:
        log.info(f"Reading category synonyms from {category_synonyms_filename}")
        category_synonyms = read_dict(category_synonyms_filename)
    else:
        category_synonyms = CaseInsensitiveDict()
    log.debug(f"Using category synonyms: {category_synonyms!r}")

    if manual_categories_filename:
        log.info(f"Reading manual categories from {manual_categories_filename}")  # noqa
        manual_categories = read_dict(manual_categories_filename)
    else:
        manual_categories = CaseInsensitiveDict()
    log.debug(f"Using manual categories: {manual_categories!r}")

    log.info(f"Writing to {results_filename!r}")
    entities_seen = set()  # type: Set[str]
    with open(results_filename, "w") as outfile:
        writer = csv.writer(outfile, dialect=output_dialect)
        if headers:
            writer.writerow(["entity", "category"])
        log.info(f"Reading entities from {entity_filename}")
        for entity_name in gen_lines_without_comments(entity_filename):
            entity_name_lower = entity_name.lower()
            if entity_name_lower in entities_seen:
                log.warning(f"Ignoring duplicate: {entity_name!r}")
                continue
            entities_seen.add(entity_name_lower)
            category = get_category(
                entity_name=entity_name,
                categories=categories,
                entity_synonyms=entity_synonyms,
                category_synonyms=category_synonyms,
                manual_categories=manual_categories,
                relationships=relationships
            ) or ""
            if category:
                log.debug(f"{entity_name} → {category}")
            else:
                log.error(f"No category found for {entity_name!r}")
            writer.writerow([entity_name, category])


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    """
    Command-line entry point.
    """
    # Parser
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--cachepath", type=str, default=DEFAULT_CACHE_PATH,
        help="Cache path for ChEBI files"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Be verbose"
    )
    subparsers = parser.add_subparsers(
        title="subcommands",
        description="Valid subcommands",
        dest="command"
    )
    subparsers.required = True

    def add_exact(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--exact_search", dest="exact_search", action="store_true",
            help="Search using exact term")
        p.add_argument(
            "--inexact_search", dest="exact_search", action="store_false",
            help="Search allowing inexact matches")
        p.set_defaults(exact_search=DEFAULT_EXACT_SEARCH)
        p.add_argument(
            "--exact_match", dest="exact_match", action="store_true",
            help="Return results for exact term only")
        p.add_argument(
            "--inexact_match", dest="exact_match", action="store_false",
            help="Return results allowing inexact matches")
        p.set_defaults(exact_match=DEFAULT_EXACT_MATCH)

    def add_entities(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "entity", type=str, nargs="+",
            help="Entity or entities to search for"
        )

    # -------------------------------------------------------------------------
    # Test
    # -------------------------------------------------------------------------
    parser_test = subparsers.add_parser(
        "test",
        help="Run some simple tests"
    )
    parser_test.set_defaults(func=lambda args: testfunc1())

    # -------------------------------------------------------------------------
    # Search
    # -------------------------------------------------------------------------
    parser_search = subparsers.add_parser(
        "search",
        help="Search for an entity in the ChEBI database"
    )
    add_entities(parser_search)
    add_exact(parser_search)
    parser_search.set_defaults(func=lambda args: search_and_list_multiple(
        search_terms=args.entity,
        exact_search=args.exact_search,
        exact_match=args.exact_match,
    ))

    # -------------------------------------------------------------------------
    # Describe
    # -------------------------------------------------------------------------
    parser_describe = subparsers.add_parser(
        "describe",
        help="Describe an entity/entities in the ChEBI database"
    )
    add_entities(parser_describe)
    add_exact(parser_describe)
    parser_describe.set_defaults(func=lambda args: search_and_describe_multiple(  # noqa
        search_terms=args.entity,
        exact_search=args.exact_search,
        exact_match=args.exact_match,
    ))

    # -------------------------------------------------------------------------
    # Ancestors
    # -------------------------------------------------------------------------
    parser_ancestors = subparsers.add_parser(
        "ancestors",
        help="Show ancestors of an entity/entities in the ChEBI database"
    )
    add_entities(parser_ancestors)
    parser_ancestors.add_argument(
        "--relationships", type=str, nargs="+",
        default=DEFAULT_ANCESTOR_RELATIONSHIPS,
        help="Relationship types that define an ancestor"
    )
    parser_ancestors.add_argument(
        "--max_generations", type=int, default=None,
        help="Number of generations to search, or None for unlimited"
    )
    parser_ancestors.set_defaults(func=lambda args: report_ancestors_multiple(
        entity_names=args.entity,
        relationships=args.relationships,
        max_generations=args.max_generations,
    ))

    # -------------------------------------------------------------------------
    # Categorize
    # -------------------------------------------------------------------------
    parser_categorize = subparsers.add_parser(
        "categorize",
        help="Categorize a list of drugs."
    )
    parser_categorize.add_argument(
        "--entities", type=str, required=True,
        help="Input file, one entity (e.g. drug) name per line."
    )
    parser_categorize.add_argument(
        "--categories", type=str, required=True,
        help="Name of file containing categories, one per line "
             "(earlier categories preferred to later)."
    )
    parser_categorize.add_argument(
        "--entity_synonyms", type=str, default=None,
        help="Name of CSV file (with optional # comments) containing synonyms "
             "in the format 'entity_from, entity_to'"
    )
    parser_categorize.add_argument(
        "--category_synonyms", type=str, default=None,
        help="Name of CSV file (with optional # comments) containing synonyms "
             "in the format 'category_from, category_to'. The translation is "
             "applied to ChEBI categories before matching. For example you "
             "can map 'EC 3.1.1.7 (acetylcholinesterase) inhibitor' to "
             "'acetylcholinesterase inhibitor' and then use only "
             "'acetylcholinesterase inhibitor' in your category file."
    )
    parser_categorize.add_argument(
        "--manual_categories", type=str, default=None,
        help="Name of CSV file (with optional # comments) containing manual "
             "categorizations in the format 'entity, category'"
    )
    parser_categorize.add_argument(
        "--results", type=str, required=True,
        help="Output CSV file."
    )
    parser_categorize.add_argument(
        "--relationships", type=str, nargs="+",
        default=DEFAULT_ANCESTOR_RELATIONSHIPS,
        help="Relationship types that define an ancestor"
    )
    parser_categorize.set_defaults(func=lambda args: categorize_from_file(
        entity_filename=args.entities,
        results_filename=args.results,
        category_filename=args.categories,
        entity_synonyms_filename=args.entity_synonyms,
        category_synonyms_filename=args.category_synonyms,
        manual_categories_filename=args.manual_categories,
        relationships=args.relationships,
    ))

    # -------------------------------------------------------------------------
    # Parse and run
    # -------------------------------------------------------------------------
    cmdargs = parser.parse_args()

    # Logging
    main_only_quicksetup_rootlogger(level=logging.DEBUG if cmdargs.verbose
                                    else logging.INFO)
    log.debug(f"ChEBI lookup from cardinal_pythonlib=={VERSION_STRING}")

    # Caching
    log.debug(f"Using cache path: {cmdargs.cachepath}")
    set_download_cache_path(cmdargs.cachepath)

    # Do something useful
    cmdargs.func(cmdargs)


if __name__ == "__main__":
    main()
