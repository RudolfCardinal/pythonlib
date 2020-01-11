#!/usr/bin/env python
# cardinal_pythonlib/athena_ohdsi.py

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

**Functions to assist with SNOMED-CT.**

See http://snomed.org/.

Note that the licensing arrangements for SNOMED-CT mean that the actual codes
must be separate (and not part of this code).

A full SNOMED CT download is about 1.1 Gb; see
https://digital.nhs.uk/services/terminology-and-classifications/snomed-ct.
Within a file such as ``uk_sct2cl_26.0.2_20181107000001.zip``, relevant files
include:

.. code-block:: none

    # Files with "Amoxicillin" in include two snapshots and two full files:

    SnomedCT_UKClinicalRF2_PRODUCTION_20181031T000001Z/Full/Terminology/sct2_Description_Full-en-GB_GB1000000_20181031.txt
    # ... 234,755 lines

    SnomedCT_InternationalRF2_PRODUCTION_20180731T120000Z/Full/Terminology/sct2_Description_Full-en_INT_20180731.txt
    # ... 2,513,953 lines; this is the main file.

Note grammar:

- http://snomed.org/scg
- https://confluence.ihtsdotools.org/display/DOCSCG
- https://confluence.ihtsdotools.org/download/attachments/33494865/SnomedCtExpo_Expressions_20161028_s2_20161101.pdf  # noqa
- https://confluence.ihtsdotools.org/display/SLPG/SNOMED+CT+Expression+Constraint+Language

Test basic expressions:

.. code-block:: python

    import logging
    from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger
    from cardinal_pythonlib.snomed import *
    main_only_quicksetup_rootlogger(level=logging.DEBUG)
    
    # ---------------------------------------------------------------------
    # From the SNOMED-CT examples (http://snomed.org/scg), with some values
    # fixed from the term browser:
    # ---------------------------------------------------------------------
    
    diabetes = SnomedConcept(73211009, "Diabetes mellitus (disorder)")
    diabetes_expr = SnomedExpression(diabetes)
    print(diabetes_expr.longform)
    print(diabetes_expr.shortform)
    
    pain = SnomedConcept(22253000, "Pain (finding)")
    finding_site = SnomedConcept(36369800, "Finding site")
    foot = SnomedConcept(56459004, "Foot")
    
    pain_in_foot = SnomedExpression(pain, {finding_site: foot})
    print(pain_in_foot.longform)
    print(pain_in_foot.shortform)
    
    amoxicillin_medicine = SnomedConcept(27658006, "Product containing amoxicillin (medicinal product)")
    amoxicillin_substance = SnomedConcept(372687004, "Amoxicillin (substance)")
    has_dose_form = SnomedConcept(411116001, "Has manufactured dose form (attribute)")
    capsule = SnomedConcept(385049006, "Capsule (basic dose form)")
    has_active_ingredient = SnomedConcept(127489000, "Has active ingredient (attribute)")
    has_basis_of_strength_substance = SnomedConcept(732943007, "Has basis of strength substance (attribute)")
    mass = SnomedConcept(118538004, "Mass, a measure of quantity of matter (property) (qualifier value)")
    unit_of_measure = SnomedConcept(767524001, "Unit of measure (qualifier value)")
    milligrams = SnomedConcept(258684004, "milligram (qualifier value)")
    
    amoxicillin_500mg_capsule = SnomedExpression(
        amoxicillin_medicine, [
            SnomedAttributeSet({has_dose_form: capsule}),
            SnomedAttributeGroup({
                has_active_ingredient: amoxicillin_substance,
                has_basis_of_strength_substance: SnomedExpression(
                    amoxicillin_substance, {
                        mass: 500,
                        unit_of_measure: milligrams,
                    }
                ),
            }),
        ]
    )
    print(amoxicillin_500mg_capsule.longform)
    print(amoxicillin_500mg_capsule.shortform)

"""  # noqa

from typing import Dict, Iterable, List, Union

from cardinal_pythonlib.reprfunc import simple_repr


# =============================================================================
# Constants
# =============================================================================

BACKSLASH = "\\"
COLON = ":"
COMMA = ","
EQUALS = "="
HASH = "#"
LBRACE = "{"
LBRACKET = "("
PIPE = "|"
PLUS = "+"
QM = '"'  # double quotation mark
RBRACE = "}"
RBRACKET = ")"
TAB = "\t"
NEWLINE = "\n"

ID_MIN_DIGITS = 6
ID_MAX_DIGITS = 18

VALUE_TYPE = Union["SnomedConcept", "SnomedExpression", int, float, str]
DICT_ATTR_TYPE = Dict["SnomedConcept", VALUE_TYPE]

SNOMED_XML_NAME = "snomed_ct_expression"


# =============================================================================
# Quoting strings
# =============================================================================

def double_quoted(s: str) -> str:
    r"""
    Returns a representation of the string argument with double quotes and
    escaped characters.

    Args:
        s: the argument

    See:

    - http://code.activestate.com/lists/python-list/272714/ -- does not work
      as null values get escaped in different ways in modern Python, and in a
      slightly unpredictable way
    - https://mail.python.org/pipermail/python-list/2003-April/236940.html --
      won't deal with repr() using triple-quotes
    - https://stackoverflow.com/questions/1675181/get-str-repr-with-double-quotes-python
      -- probably the right general approach

    Test code:

    .. code-block:: python

        from cardinal_pythonlib.snomed import double_quoted
        
        def test(s):
            print(f"double_quoted({s!r}) -> {double_quoted(s)}")
        
        
        test("ab'cd")
        test("ab'c\"d")
        test('ab"cd')

    """  # noqa
    # For efficiency, we use a list:
    # https://stackoverflow.com/questions/3055477/how-slow-is-pythons-string-concatenation-vs-str-join  # noqa
    # https://waymoot.org/home/python_string/
    dquote = '"'
    ret = [dquote]  # type: List[str]
    for c in s:
        # "Named" characters
        if c == NEWLINE:
            ret.append(r"\n")
        elif c == TAB:
            ret.append(r"\t")
        elif c == QM:
            ret.append(r'\"')
        elif c == BACKSLASH:
            ret.append(r"\\")
        elif ord(c) < 32:
            # two-digit hex format, e.g. \x1F for ASCII 31
            ret.append(fr"\x{ord(c):02X}")
        else:
            ret.append(c)
    ret.append(dquote)
    return "".join(ret)


# =============================================================================
# SNOMED-CT concepts
# =============================================================================

class SnomedBase(object):
    """
    Common functions for SNOMED-CT classes
    """
    def as_string(self, longform: bool = True) -> str:
        """
        Returns the string form.

        Args:
            longform: print SNOMED-CT concepts in long form?
        """
        raise NotImplementedError("implement in subclass")

    @property
    def shortform(self) -> str:
        """
        Returns the short form, without terms.
        """
        return self.as_string(False)

    @property
    def longform(self) -> str:
        return self.as_string(True)

    def __str__(self) -> str:
        return self.as_string(True)


class SnomedConcept(SnomedBase):
    """
    Represents a SNOMED concept with its description (associated term).
    """
    def __init__(self, identifier: int, term: str) -> None:
        """
        Args:
            identifier: SNOMED-CT identifier (code)
            term: associated term (description)
        """
        assert isinstance(identifier, int), (
            f"SNOMED-CT concept identifier is not an integer: {identifier!r}"
        )
        ndigits = len(str(identifier))
        assert ID_MIN_DIGITS <= ndigits <= ID_MAX_DIGITS, (
            f"SNOMED-CT concept identifier has wrong number of digits: "
            f"{identifier!r}"
        )
        assert PIPE not in term, (
            f"SNOMED-CT term has invalid pipe character: {term!r}"
        )
        self.identifier = identifier
        self.term = term

    def __repr__(self) -> str:
        return simple_repr(self, ["identifier", "term"])

    def as_string(self, longform: bool = True) -> str:
        # Docstring in base class.
        if longform:
            return f"{self.identifier} {PIPE}{self.term}{PIPE}"
        else:
            return str(self.identifier)

    def concept_reference(self, longform: bool = True) -> str:
        """
        Returns one of the string representations.

        Args:
            longform: in long form, with the description (associated term)?
        """
        return self.as_string(longform)


# =============================================================================
# SNOMED-CT expressions
# =============================================================================

class SnomedValue(SnomedBase):
    """
    Represents a value: either a concrete value (e.g. int, float, str), or a
    SNOMED-CT concept/expression.

    Implements the grammar elements: attributeValue, expressionValue,
    stringValue, numericValue, integerValue, decimalValue.
    """
    def __init__(self, value: VALUE_TYPE) -> None:
        """
        Args:
            value: the value
        """
        assert isinstance(value, (SnomedConcept, SnomedExpression,
                                  int, float, str)), (
            f"Invalid value type to SnomedValue: {value!r}"
        )
        self.value = value

    def as_string(self, longform: bool = True) -> str:
        # Docstring in base class
        x = self.value
        if isinstance(x, SnomedConcept):
            return x.concept_reference(longform)
        elif isinstance(x, SnomedExpression):
            # As per p16 of formal reference cited above.
            return f"{LBRACKET} {x.as_string(longform)} {RBRACKET}"
        elif isinstance(x, (int, float)):
            return HASH + str(x)
        elif isinstance(x, str):
            # On the basis that SNOMED's "QM" (quote mark) is 0x22, the double
            # quote:
            return double_quoted(x)
        else:
            raise ValueError("Bad input value type")

    def __repr__(self) -> str:
        return simple_repr(self, ["value"])


class SnomedFocusConcept(SnomedBase):
    """
    Represents a SNOMED-CT focus concept, which is one or more concepts.
    """
    def __init__(self,
                 concept: Union[SnomedConcept, Iterable[SnomedConcept]]) \
            -> None:
        """
        Args:
            concept: the core concept(s); a :class:`SnomedCode` or an
                iterable of them
        """
        if isinstance(concept, SnomedConcept):
            self.concepts = [concept]
        else:
            self.concepts = list(concept)
        assert all(isinstance(x, SnomedConcept) for x in self.concepts)

    def as_string(self, longform: bool = True) -> str:
        # Docstring in base class.
        sep = " " + PLUS + " "
        return sep.join(c.concept_reference(longform) for c in self.concepts)

    def __repr__(self) -> str:
        return simple_repr(self, ["concepts"])


class SnomedAttribute(SnomedBase):
    """
    Represents a SNOMED-CT attribute, being a name/value pair.
    """
    def __init__(self, name: SnomedConcept, value: VALUE_TYPE) -> None:
        """
        Args:
            name: a :class:`SnomedConcept` (attribute name)
            value: an attribute value (:class:`SnomedConcept`, number, or
                string)
        """
        assert isinstance(name, SnomedConcept)
        if not isinstance(value, SnomedValue):
            value = SnomedValue(value)
        self.name = name
        self.value = value

    def as_string(self, longform: bool = True) -> str:
        # Docstring in base class.
        return (
            f"{self.name.concept_reference(longform)} {EQUALS} "
            f"{self.value.as_string(longform)}"
        )

    def __repr__(self) -> str:
        return simple_repr(self, ["name", "value"])


class SnomedAttributeSet(SnomedBase):
    """
    Represents an attribute set.
    """
    def __init__(self, attributes: Union[DICT_ATTR_TYPE,
                                         Iterable[SnomedAttribute]]) -> None:
        """
        Args:
            attributes: the attributes
        """
        if isinstance(attributes, dict):
            self.attributes = [SnomedAttribute(k, v)
                               for k, v in attributes.items()]
        else:
            self.attributes = list(attributes)
        assert all(isinstance(x, SnomedAttribute) for x in self.attributes)

    def as_string(self, longform: bool = True) -> str:
        # Docstring in base class.
        attrsep = COMMA + " "
        return attrsep.join(attr.as_string(longform)
                            for attr in self.attributes)

    def __repr__(self) -> str:
        return simple_repr(self, ["attributes"])


class SnomedAttributeGroup(SnomedBase):
    """
    Represents a collected group of attribute/value pairs.
    """
    def __init__(self, attribute_set: Union[DICT_ATTR_TYPE,
                                            SnomedAttributeSet]) -> None:
        """
        Args:
            attribute_set: a :class:`SnomedAttributeSet` to group
        """
        if isinstance(attribute_set, dict):
            attribute_set = SnomedAttributeSet(attribute_set)
        assert isinstance(attribute_set, SnomedAttributeSet)
        self.attribute_set = attribute_set

    def as_string(self, longform: bool = True) -> str:
        # Docstring in base class.
        return f"{LBRACE} {self.attribute_set.as_string(longform)} {RBRACE}"

    def __repr__(self) -> str:
        return simple_repr(self, ["attribute_set"])


class SnomedRefinement(SnomedBase):
    """
    Implements a SNOMED-CT "refinement", which is an attribute set +/- some
    attribute groups.
    """
    def __init__(self,
                 refinements: Union[DICT_ATTR_TYPE,
                                    Iterable[Union[SnomedAttributeSet,
                                                   SnomedAttributeGroup]]]) \
            -> None:
        """
        Args:
            refinements: iterable of :class:`SnomedAttributeSet` (but only
                zero or one) and :class:`SnomedAttributeGroup` objects
        """
        if isinstance(refinements, dict):
            refinements = [SnomedAttributeSet(refinements)]
        self.attrsets = []  # type: List[SnomedBase]
        self.attrgroups = []  # type: List[SnomedBase]
        for r in refinements:
            if isinstance(r, SnomedAttributeSet):
                if self.attrsets:
                    raise ValueError("Only one SnomedAttributeSet allowed "
                                     "to SnomedRefinement")
                self.attrsets.append(r)
            elif isinstance(r, SnomedAttributeGroup):
                self.attrgroups.append(r)
            else:
                raise ValueError(f"Unknown object to SnomedRefinement: {r!r}")

    def as_string(self, longform: bool = True) -> str:
        # Docstring in base class.
        # Ungrouped before grouped; see 6.5 in "SNOMED CT Compositional Grammar
        # v2.3.1"
        sep = COMMA + " "
        return sep.join(x.as_string(longform)
                        for x in self.attrsets + self.attrgroups)

    def __repr__(self) -> str:
        return simple_repr(self, ["attrsets", "attrgroups"])


class SnomedExpression(SnomedBase):
    """
    An expression containing several SNOMED-CT codes in relationships.
    """
    def __init__(self,
                 focus_concept: Union[SnomedConcept, SnomedFocusConcept],
                 refinement: Union[SnomedRefinement,
                                   DICT_ATTR_TYPE,
                                   List[Union[SnomedAttributeSet,
                                              SnomedAttributeGroup]]] = None) \
            -> None:
        """
        Args:
            focus_concept: the core concept(s); a :class:`SnomedFocusConcept`
            refinement: optional additional information; a
                :class:`SnomedRefinement` or a dictionary or list that can be
                converted to one
        """
        if isinstance(focus_concept, SnomedConcept):
            focus_concept = SnomedFocusConcept(focus_concept)
        assert isinstance(focus_concept, SnomedFocusConcept)
        if isinstance(refinement, (dict, list)):
            refinement = SnomedRefinement(refinement)
        if refinement is not None:
            assert isinstance(refinement, SnomedRefinement)
        self.focus_concept = focus_concept
        self.refinement = refinement

    def as_string(self, longform: bool = True) -> str:
        # Docstring in base class.
        s = self.focus_concept.as_string(longform)
        if self.refinement:
            s += " " + COLON + " " + self.refinement.as_string(longform)
        return s

    def __repr__(self) -> str:
        return simple_repr(self, ["focus_concept", "refinement"])
