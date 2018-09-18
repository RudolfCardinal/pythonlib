#!/usr/bin/env python
# cardinal_pythonlib/django/fields/jsonclassfield.py

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

**Django field class implementing storage of arbitrary Python objects in a
database, so long as they are serializable to/from JSON.**

- We were using ``django-picklefield`` and ``PickledObjectField``.

- However, this fails in a nasty way if you add new attributes to a class
  that has been pickled, and anyway pickle is insecure (as it trusts its
  input).
  
- JSON is better.
  http://www.benfrederickson.com/dont-pickle-your-data/

- JSON fields in Django:
  https://djangopackages.org/grids/g/json-fields/

- http://paltman.com/how-to-store-arbitrary-data-in-a-django-model/

- Native Django JSONField requires PostgreSQL, and is not part of the core set
  of fields:

  https://docs.djangoproject.com/en/1.10/ref/contrib/postgres/fields/#django.contrib.postgres.fields.JSONField
  https://docs.djangoproject.com/en/1.10/ref/models/fields/

- http://stackoverflow.com/questions/6578986/how-to-convert-json-data-into-a-python-object
- http://stackoverflow.com/questions/31235771/is-parsing-a-json-naively-into-a-python-class-or-struct-secure
- http://stackoverflow.com/questions/16405969/how-to-change-json-encoding-behaviour-for-serializable-python-object/16406798#16406798
- http://stackoverflow.com/questions/3768895/how-to-make-a-class-json-serializable

e.g.:

.. code-block:: python
    
    import inspect
    import json
    from typing import Any, Dict, Union
    
    class Thing(object):
        def __init__(self, a: int = 1, b: str = ''):
            self.a = a
            self.b = b
        def __repr__(self) -> str:
            return "<Thing(a={}, b={}) at {}>".format(
                repr(self.a), repr(self.b), hex(id(self)))
    
    
    MY_JSON_TYPES = {
        'Thing': Thing,
    }
    TYPE_LABEL = '__type__'
    
    class MyEncoder(json.JSONEncoder):
        def default(self, obj: Any) -> Any:
            typename = type(obj).__name__
            if typename in MY_JSON_TYPES.keys():
                d = obj.__dict__
                d[TYPE_LABEL] = typename
                return d
            return super().default(obj)
    
    
    class MyDecoder(json.JSONDecoder):  # INADEQUATE for nested things
        def decode(self, s: str) -> Any:
            o = super().decode(s)
            if isinstance(o, dict):
                typename = o.get(TYPE_LABEL, '')
                if typename and typename in MY_JSON_TYPES:
                    classtype = MY_JSON_TYPES[typename]
                    o.pop(TYPE_LABEL)
                    return classtype(**o)
            return o
    
    
    def my_decoder_hook(d: Dict) -> Any:
        if TYPE_LABEL in d:
            typename = d.get(TYPE_LABEL, '')
            if typename and typename in MY_JSON_TYPES:
                classtype = MY_JSON_TYPES[typename]
                d.pop(TYPE_LABEL)
                return classtype(**d)
        return d
    
    
    x = Thing(a=5, b="hello")
    y = [1, x, 2]
    
    # Encoding:
    j = MyEncoder().encode(x)  # OK
    j2 = json.dumps(x, cls=MyEncoder)  # OK; same result
    
    k = MyEncoder().encode(y)  # OK
    k2 = json.dumps(y, cls=MyEncoder)  # OK; same result
    
    # Decoding
    x2 = MyDecoder().decode(j)  # OK, but simple structure
    y2 = MyDecoder().decode(k)  # FAILS
    y3 = json.JSONDecoder(object_hook=my_decoder_hook).decode(k)  # SUCCEEDS
    
    print(repr(x))
    print(repr(x2))

"""  # noqa

from django.core.exceptions import ValidationError
from django.db.models import TextField

from cardinal_pythonlib.json.serialize import json_decode, json_encode


# =============================================================================
# Django field
# - To use a class with this, the class must be registered with
#   register_class_for_json() above. Register the class immediately after
#   defining it.
# =============================================================================

class JsonClassField(TextField):
    """
    Django field that serializes Python objects into JSON.
    """
    # https://docs.djangoproject.com/en/1.10/howto/custom-model-fields/
    description = "Python objects serialized into JSON"

    # No need to implement __init__()
    # No need to implement deconstruct()
    # No need to implement db_type()

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def from_db_value(self, value, expression, connection, context):
        """
        "Called in all circumstances when the data is loaded from the
        database, including in aggregates and values() calls."
        """
        if value is None:
            return value
        return json_decode(value)

    def to_python(self, value):
        """
        "Called during deserialization and during the clean() method used
        from forms.... [s]hould deal gracefully with... (*) an instance of
        the correct type; (*) a string; (*) None (if the field allows
        null=True)."

        "For ``to_python()``, if anything goes wrong during value conversion,
        you should raise a ``ValidationError`` exception."
        """
        if value is None:
            return value
        if not isinstance(value, str):
            return value
        try:
            return json_decode(value)
        except Exception as err:
            raise ValidationError(repr(err))

    def get_prep_value(self, value):
        """
        Converse of ``to_python()``. Converts Python objects back to query
        values.
        """
        return json_encode(value)
