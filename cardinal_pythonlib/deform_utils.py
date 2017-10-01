#!/usr/bin/env python
# cardinal_pythonlib/deform_utils.py

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
from typing import (Any, Callable, Dict, Generator, Iterable, List, Tuple,
                    TYPE_CHECKING)

from cardinal_pythonlib.logs import BraceStyleAdapter
from colander import Invalid, SchemaNode
from deform.exception import ValidationFailure
from deform.field import Field
from deform.form import Form
from deform.widget import HiddenWidget

if TYPE_CHECKING:
    from pyramid.request import Request

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceStyleAdapter(log)

ValidatorType = Callable[[SchemaNode, Any], None]  # called as v(node, value)

# =============================================================================
# Debugging options
# =============================================================================

DEBUG_DYNAMIC_DESCRIPTIONS_FORM = False
DEBUG_FORM_VALIDATION = False

if any([DEBUG_DYNAMIC_DESCRIPTIONS_FORM, DEBUG_FORM_VALIDATION]):
    log.warning("Debugging options enabled!")


# =============================================================================
# Widget resources
# =============================================================================

def get_head_form_html(req: "Request", forms: List[Form]) -> str:
    """
    Returns the extra HTML that needs to be injected into the <head> section
    for a Deform form to work properly.
    """
    # https://docs.pylonsproject.org/projects/deform/en/latest/widget.html#widget-requirements
    js_resources = []  # type: List[str]
    css_resources = []  # type: List[str]
    for form in forms:
        resources = form.get_widget_resources()  # type: Dict[str, List[str]]
        # Add, ignoring duplicates:
        js_resources.extend(x for x in resources['js']
                            if x not in js_resources)
        css_resources.extend(x for x in resources['css']
                             if x not in css_resources)
    js_links = [req.static_url(r) for r in js_resources]
    css_links = [req.static_url(r) for r in css_resources]
    js_tags = ['<script type="text/javascript" src="%s"></script>' % link
               for link in js_links]
    css_tags = ['<link rel="stylesheet" href="%s"/>' % link
                for link in css_links]
    tags = js_tags + css_tags
    head_html = "\n".join(tags)
    return head_html


# =============================================================================
# Debugging form errors (which can be hidden in their depths)
# =============================================================================
# I'm not alone in the problem of errors from a HiddenWidget:
# https://groups.google.com/forum/?fromgroups#!topic/pylons-discuss/LNHDq6KvNLI
# https://groups.google.com/forum/#!topic/pylons-discuss/Lr1d1VpMycU

class DeformErrorInterface(object):
    def __init__(self, msg: str, *children: "DeformErrorInterface") -> None:
        self._msg = msg
        self.children = children

    def __str__(self) -> str:
        return self._msg


class InformativeForm(Form):
    def validate(self,
                 controls: Iterable[Tuple[str, str]],  # list of key/value pairs  # noqa
                 subcontrol: str = None) -> Any:
        """Returns a Colander appstruct, or raises."""
        try:
            return super().validate(controls, subcontrol)
        except ValidationFailure as e:
            if DEBUG_FORM_VALIDATION:
                log.warning("Validation failure: {!r}; {}",
                            e, self._get_form_errors())
            self._show_hidden_widgets_for_fields_with_errors(self)
            raise

    def _show_hidden_widgets_for_fields_with_errors(self,
                                                    field: Field) -> None:
        if field.error:
            widget = getattr(field, "widget", None)
            # log.warning(repr(widget))
            # log.warning(repr(widget.hidden))
            if widget is not None and widget.hidden:
                # log.critical("Found hidden widget for field with error!")
                widget.hidden = False
        for child_field in field.children:
            self._show_hidden_widgets_for_fields_with_errors(child_field)

    def _collect_error_errors(self,
                              errorlist: List[str],
                              error: DeformErrorInterface) -> None:
        if error is None:
            return
        errorlist.append(str(error))
        for child_error in error.children:  # typically: subfields
            self._collect_error_errors(errorlist, child_error)

    def _collect_form_errors(self,
                             errorlist: List[str],
                             field: Field,
                             hidden_only: bool = False):
        if hidden_only:
            widget = getattr(field, "widget", None)
            if not isinstance(widget, HiddenWidget):
                return
        # log.critical(repr(field))
        self._collect_error_errors(errorlist, field.error)
        for child_field in field.children:
            self._collect_form_errors(errorlist, child_field,
                                      hidden_only=hidden_only)

    def _get_form_errors(self, hidden_only: bool = False) -> str:
        errorlist = []  # type: List[str]
        self._collect_form_errors(errorlist, self, hidden_only=hidden_only)
        return "; ".join(repr(e) for e in errorlist)


def debug_validator(validator: ValidatorType) -> ValidatorType:
    """
    Use as a wrapper around a validator, e.g.
        self.validator = debug_validator(OneOf(["some", "values"]))
    """
    def _validate(node: SchemaNode, value: Any) -> None:
        log.debug("Validating: {!r}", value)
        try:
            validator(node, value)
            log.debug("... accepted")
        except Invalid:
            log.debug("... rejected")
            raise

    return _validate


# =============================================================================
# DynamicDescriptionsForm
# =============================================================================

def gen_fields(field: Field) -> Generator[Field, None, None]:
    yield field
    for c in field.children:
        for f in gen_fields(c):
            yield f


class DynamicDescriptionsForm(InformativeForm):
    """
    For explanation, see ValidateDangerousOperationNode().

    In essence, this allows a schema to change its "description" properties
    during form validation, and then to have them reflected in the form (which
    won't happen with a standard Deform Form, since it normally copies its
    descriptions from its schema at creation time).

    The upshot is that we can store temporary values in a form and validate
    against them.

    The use case is to generate a random string which the user has to enter to
    confirm dangerous operations.
    """
    def __init__(self,
                 *args,
                 dynamic_descriptions: bool = True,
                 dynamic_titles: bool = False,
                 **kwargs) -> None:
        self.dynamic_descriptions = dynamic_descriptions
        self.dynamic_titles = dynamic_titles
        super().__init__(*args, **kwargs)

    def validate(self,
                 controls: Iterable[Tuple[str, str]],
                 subcontrol: str = None) -> Any:
        try:
            return super().validate(controls, subcontrol)
        finally:
            for f in gen_fields(self):
                if self.dynamic_titles:
                    if DEBUG_DYNAMIC_DESCRIPTIONS_FORM:
                        log.debug("Rewriting title for {!r} from {!r} to {!r}",
                                  f, f.title, f.schema.title)
                    f.title = f.schema.title
                if self.dynamic_descriptions:
                    if DEBUG_DYNAMIC_DESCRIPTIONS_FORM:
                        log.debug(
                            "Rewriting description for {!r} from {!r} to {!r}",
                            f, f.description, f.schema.description)
                    f.description = f.schema.description
