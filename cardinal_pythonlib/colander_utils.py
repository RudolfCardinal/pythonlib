#!/usr/bin/env python
# cardinal_pythonlib/colander_utils.py

"""
===============================================================================

    Original code copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

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

**Functions for working with colander.**

Colander: https://docs.pylonsproject.org/projects/colander/en/latest/

"""


import logging
import random
from typing import (Any, Callable, Dict, Iterable, List, Optional,
                    Tuple, TYPE_CHECKING, Union)

from cardinal_pythonlib.datetimefunc import (
    coerce_to_pendulum,
    PotentialDatetimeType,
)
from cardinal_pythonlib.logs import BraceStyleAdapter
import colander
from colander import (
    Boolean,
    Date,
    DateTime,  # NB name clash with pendulum
    Email,
    Integer,
    Invalid,
    Length,
    MappingSchema,
    SchemaNode,
    SchemaType,
    String,
)
from deform.widget import (
    CheckboxWidget,
    DateTimeInputWidget,
    HiddenWidget,
)
from pendulum import DateTime as Pendulum  # NB name clash with colander
from pendulum.parsing.exceptions import ParserError

if TYPE_CHECKING:
    # noinspection PyProtectedMember
    from colander import _SchemaNode

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceStyleAdapter(log)

ColanderNullType = type(colander.null)
ValidatorType = Callable[[SchemaNode, Any], None]  # called as v(node, value)

# =============================================================================
# Debugging options
# =============================================================================

DEBUG_DANGER_VALIDATION = False

if DEBUG_DANGER_VALIDATION:
    log.warning("Debugging options enabled!")

# =============================================================================
# Constants
# =============================================================================

EMAIL_ADDRESS_MAX_LEN = 255  # https://en.wikipedia.org/wiki/Email_address
SERIALIZED_NONE = ""  # has to be a string; avoid "None" like the plague!


# =============================================================================
# New generic SchemaType classes
# =============================================================================

class PendulumType(SchemaType):
    """
    Colander :class:`SchemaType` for :class:`Pendulum` date/time objects.
    """
    def __init__(self, use_local_tz: bool = True):
        self.use_local_tz = use_local_tz
        super().__init__()  # not necessary; SchemaType has no __init__

    def serialize(self,
                  node: SchemaNode,
                  appstruct: Union[PotentialDatetimeType,
                                   ColanderNullType]) \
            -> Union[str, ColanderNullType]:
        """
        Serializes Python object to string representation.
        """
        if not appstruct:
            return colander.null
        try:
            appstruct = coerce_to_pendulum(appstruct,
                                           assume_local=self.use_local_tz)
        except (ValueError, ParserError) as e:
            raise Invalid(
                node,
                "{!r} is not a pendulum.DateTime object; error was "
                "{!r}".format(appstruct, e))
        return appstruct.isoformat()

    def deserialize(self,
                    node: SchemaNode,
                    cstruct: Union[str, ColanderNullType]) \
            -> Optional[Pendulum]:
        """
        Deserializes string representation to Python object.
        """
        if not cstruct:
            return colander.null
        try:
            result = coerce_to_pendulum(cstruct,
                                        assume_local=self.use_local_tz)
        except (ValueError, ParserError) as e:
            raise Invalid(node, "Invalid date/time: value={!r}, error="
                                "{!r}".format(cstruct, e))
        return result


class AllowNoneType(SchemaType):
    """
    Serializes ``None`` to ``''``, and deserializes ``''`` to ``None``;
    otherwise defers to the parent type.

    A type which accepts serializing ``None`` to ``''`` and deserializing
    ``''`` to ``None``. When the value is not equal to ``None``/``''``, it will
    use (de)serialization of the given type. This can be used to make nodes
    optional.

    Example:

    .. code-block:: python

        date = colander.SchemaNode(
            colander.NoneType(colander.DateTime()),
            default=None,
            missing=None,
        )

    NOTE ALSO that Colander nodes explicitly never validate a missing value;
    see ``colander/__init__.py``, in :func:`_SchemaNode.deserialize`. We want
    them to do so, essentially so we can pass in ``None`` to a form but have
    the form refuse to validate if it's still ``None`` at submission.

    """
    def __init__(self, type_: SchemaType) -> None:
        self.type_ = type_

    def serialize(self, node: SchemaNode,
                  value: Any) -> Union[str, ColanderNullType]:
        """
        Serializes Python object to string representation.
        """
        if value is None:
            retval = ''
        else:
            # noinspection PyUnresolvedReferences
            retval = self.type_.serialize(node, value)
        # log.debug("AllowNoneType.serialize: {!r} -> {!r}", value, retval)
        return retval

    def deserialize(self, node: SchemaNode,
                    value: Union[str, ColanderNullType]) -> Any:
        """
        Deserializes string representation to Python object.
        """
        if value is None or value == '':
            retval = None
        else:
            # noinspection PyUnresolvedReferences
            retval = self.type_.deserialize(node, value)
        # log.debug("AllowNoneType.deserialize: {!r} -> {!r}", value, retval)
        return retval


# =============================================================================
# Node helper functions
# =============================================================================

def get_values_and_permissible(values: Iterable[Tuple[Any, str]],
                               add_none: bool = False,
                               none_description: str = "[None]") \
        -> Tuple[List[Tuple[Any, str]], List[Any]]:
    """
    Used when building Colander nodes.

    Args:
        values: an iterable of tuples like ``(value, description)`` used in
            HTML forms

        add_none: add a tuple ``(None, none_description)`` at the start of
            ``values`` in the result?

        none_description: the description used for ``None`` if ``add_none``
            is set

    Returns:
        a tuple ``(values, permissible_values)``, where

        - ``values`` is what was passed in (perhaps with the addition of the
          "None" tuple at the start)
        - ``permissible_values`` is a list of all the ``value`` elements of
          the original ``values``

    """
    permissible_values = list(x[0] for x in values)
    # ... does not include the None value; those do not go to the validator
    if add_none:
        none_tuple = (SERIALIZED_NONE, none_description)
        values = [none_tuple] + list(values)
    return values, permissible_values


class EmailValidatorWithLengthConstraint(Email):
    """
    The Colander ``Email`` validator doesn't check length. This does.
    """
    def __init__(self, *args, min_length: int = 0, **kwargs) -> None:
        self._length = Length(min_length, EMAIL_ADDRESS_MAX_LEN)
        super().__init__(*args, **kwargs)

    def __call__(self, node: SchemaNode, value: Any) -> None:
        self._length(node, value)
        super().__call__(node, value)  # call Email regex validator


# =============================================================================
# Other new generic SchemaNode classes
# =============================================================================
# Note that we must pass both *args and **kwargs upwards, because SchemaNode
# does some odd stuff with clone().

class OptionalIntNode(SchemaNode):
    """
    Colander node accepting integers but also blank values (i.e. it's
    optional).
    """
    # YOU CANNOT USE ARGUMENTS THAT INFLUENCE THE STRUCTURE, because these Node
    # objects get default-copied by Deform.
    @staticmethod
    def schema_type() -> SchemaType:
        return AllowNoneType(Integer())

    default = None
    missing = None


class OptionalStringNode(SchemaNode):
    """
    Colander node accepting strings but allowing them to be blank (optional).

    Coerces None to ``""`` when serializing; otherwise it is coerced to
    ``"None"``, i.e. a string literal containing the word "None", which is much
    more wrong.
    """
    @staticmethod
    def schema_type() -> SchemaType:
        return AllowNoneType(String(allow_empty=True))

    default = ""
    missing = ""


class MandatoryStringNode(SchemaNode):
    """
    Colander string node, where the string is obligatory.

    CAVEAT: WHEN YOU PASS DATA INTO THE FORM, YOU MUST USE

    .. code-block:: python

        appstruct = {
            somekey: somevalue or "",
            #                  ^^^^^
            #                  without this, None is converted to "None"
        }
    """
    @staticmethod
    def schema_type() -> SchemaType:
        return String(allow_empty=False)


class HiddenIntegerNode(OptionalIntNode):
    """
    Colander node containing an integer, that is hidden to the user.
    """
    widget = HiddenWidget()


class HiddenStringNode(OptionalStringNode):
    """
    Colander node containing an optional string, that is hidden to the user.
    """
    widget = HiddenWidget()


class DateTimeSelectorNode(SchemaNode):
    """
    Colander node containing a date/time.
    """
    schema_type = DateTime
    missing = None


class DateSelectorNode(SchemaNode):
    """
    Colander node containing a date.
    """
    schema_type = Date
    missing = None


class OptionalPendulumNode(SchemaNode):
    """
    Colander node containing an optional :class:`Pendulum` date/time.
    """
    @staticmethod
    def schema_type() -> SchemaType:
        return AllowNoneType(PendulumType())

    default = None
    missing = None
    widget = DateTimeInputWidget()


class BooleanNode(SchemaNode):
    """
    Colander node representing a boolean value with a checkbox widget.
    """
    schema_type = Boolean
    widget = CheckboxWidget()

    def __init__(self, *args, title: str = "?", label: str = "",
                 default: bool = False, **kwargs) -> None:
        self.title = title  # above the checkbox
        self.label = label or title  # to the right of the checkbox
        self.default = default
        self.missing = default
        super().__init__(*args, **kwargs)


class ValidateDangerousOperationNode(MappingSchema):
    """
    Colander node that can be added to forms allowing dangerous operations
    (e.g. deletion of data). The node shows the user a code and requires the
    user to type that code in, before it will permit the form to proceed.

    For this to work, the containing form *must* inherit from
    :class:`DynamicDescriptionsForm` with ``dynamic_descriptions=True``.

    Usage is simple, like this:

    .. code-block:: python

        class AddSpecialNoteSchema(CSRFSchema):
            table_name = HiddenStringNode()
            server_pk = HiddenIntegerNode()
            note = MandatoryStringNode(widget=TextAreaWidget(rows=20, cols=80))
            danger = ValidateDangerousOperationNode()

    """
    target = HiddenStringNode()
    user_entry = MandatoryStringNode(title="Validate this dangerous operation")

    def __init__(self, *args, length: int = 4, allowed_chars: str = None,
                 **kwargs) -> None:
        """
        Args:
            length: code length required from the user
            allowed_chars: string containing the permitted characters
                (by default, digits)
        """
        self.allowed_chars = allowed_chars or "0123456789"
        self.length = length
        super().__init__(*args, **kwargs)

    # noinspection PyUnusedLocal
    def after_bind(self, node: SchemaNode, kw: Dict[str, Any]) -> None:
        # Accessing the nodes is fiddly!
        target_node = next(c for c in self.children if c.name == 'target')  # type: _SchemaNode  # noqa
        # Also, this whole thing is a bit hard to get your head around.
        # - This function will be called every time the form is accessed.
        # - The first time (fresh form load), there will be no value in
        #   "target", so we set "target.default", and "target" will pick up
        #   that default value.
        # - On subsequent times (e.g. form submission), there will be a value
        #   in "target", so the default is irrelevant.
        # - This matters because we want "user_entry_node.description" to
        #   be correct.
        # - Actually, easier is just to make "target" a static display?
        #   No; if you use widget=TextInputWidget(readonly=True), there is no
        #   form value rendered.
        # - But it's hard to get the new value out of "target" at this point.
        # - Should we do that in validate()?
        # - No: on second rendering, after_bind() is called, and then
        #   validator() is called, but the visible form reflects changes made
        #   by after_bind() but NOT validator(); presumably Deform pulls the
        #   contents in between those two. Hmm.
        # - Particularly "hmm" as we don't have access to form data at the
        #   point of after_bind().
        # - The problem is probably that deform.field.Field.__init__ copies its
        #   schema.description. Yes, that's the problem.
        # - So: a third option: a display value (which we won't get back) as
        #   well as a hidden value that we will? No, no success.
        # - Or a fourth: something whose "description" is a property, not a
        #   str? No -- when you copy a property, you copy the value not the
        #   function.
        # - Fifthly: a new DangerValidationForm that rewrites its field
        #   descriptions after validation. That works!
        target_value = ''.join(random.choice(self.allowed_chars)
                               for i in range(self.length))
        target_node.default = target_value
        # Set the description:
        if DEBUG_DANGER_VALIDATION:
            log.debug("after_bind: setting description to {!r}", target_value)
        self.set_description(target_value)
        # ... may be overridden immediately by validator() if this is NOT the
        #     first rendering

    def validator(self, node: SchemaNode, value: Any) -> None:
        user_entry_value = value['user_entry']
        target_value = value['target']
        # Set the description:
        if DEBUG_DANGER_VALIDATION:
            log.debug("validator: setting description to {!r}", target_value)
        self.set_description(target_value)
        # arse!
        value['display_target'] = target_value
        # Check the value
        if user_entry_value != target_value:
            raise Invalid(
                node,
                "Not correctly validated (user_entry_value={!r}, "
                "target_value={!r}".format(user_entry_value, target_value))

    def set_description(self, target_value: str) -> None:
        user_entry_node = next(c for c in self.children
                               if c.name == 'user_entry')  # type: _SchemaNode
        prefix = "Please enter the following: "
        user_entry_node.description = prefix + target_value
        if DEBUG_DANGER_VALIDATION:
            log.debug("user_entry_node.description: {!r}",
                      user_entry_node.description)
