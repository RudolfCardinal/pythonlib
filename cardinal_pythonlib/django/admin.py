#!/usr/bin/env python
# cardinal_pythonlib/django/admin.py

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

**Helper functions for the Django admin site.**

"""

from typing import Any, Callable

from django.contrib.admin import AdminSite, ModelAdmin
# from django.db.models import Model
from django.utils.html import escape
from django.urls import reverse


# =============================================================================
# Disable boolean icons for a ModelAdmin field
# =============================================================================
# http://stackoverflow.com/questions/13990846/disable-on-off-icon-for-boolean-field-in-django  # noqa
# ... extended to use closures

def disable_bool_icon(
        fieldname: str,
        model) -> Callable[[Any], bool]:
    """
    Disable boolean icons for a Django ModelAdmin field.
    The '_meta' attribute is present on Django model classes and instances.

    model_class: ``Union[Model, Type[Model]]``

    ... only the type checker in Py3.5 is broken; see ``files.py``
    """
    # noinspection PyUnusedLocal
    def func(self, obj):
        return getattr(obj, fieldname)
    func.boolean = False
    func.admin_order_field = fieldname
    # func.short_description = \
    #     model._meta.get_field_by_name(fieldname)[0].verbose_name
    # get_field_by_name() deprecated in Django 1.9 and will go in 1.10
    # https://docs.djangoproject.com/en/1.8/ref/models/meta/

    # noinspection PyProtectedMember, PyUnresolvedReferences
    func.short_description = \
        model._meta.get_field(fieldname).verbose_name
    return func


# =============================================================================
# Links in model admin
# =============================================================================

# noinspection PyProtectedMember
def admin_view_url(admin_site: AdminSite,
                   obj,
                   view_type: str = "change",
                   current_app: str = None) -> str:
    """
    Get a Django admin site URL for an object.
    """
    app_name = obj._meta.app_label.lower()
    model_name = obj._meta.object_name.lower()
    pk = obj.pk
    viewname = "admin:{}_{}_{}".format(app_name, model_name, view_type)
    if current_app is None:
        current_app = admin_site.name
    url = reverse(viewname, args=[pk], current_app=current_app)
    return url


# noinspection PyProtectedMember
def admin_view_fk_link(modeladmin: ModelAdmin,
                       obj,
                       fkfield: str,
                       missing: str = "(None)",
                       use_str: bool = True,
                       view_type: str = "change",
                       current_app: str = None) -> str:
    """
    Get a Django admin site URL for an object that's found from a foreign
    key in our object of interest.
    """
    if not hasattr(obj, fkfield):
        return missing
    linked_obj = getattr(obj, fkfield)
    app_name = linked_obj._meta.app_label.lower()
    model_name = linked_obj._meta.object_name.lower()
    viewname = "admin:{}_{}_{}".format(app_name, model_name, view_type)
    # https://docs.djangoproject.com/en/dev/ref/contrib/admin/#reversing-admin-urls  # noqa
    if current_app is None:
        current_app = modeladmin.admin_site.name
        # ... plus a bit of home-grown magic; see Django source
    url = reverse(viewname, args=[linked_obj.pk], current_app=current_app)
    if use_str:
        label = escape(str(linked_obj))
    else:
        label = "{} {}".format(escape(linked_obj._meta.object_name),
                               linked_obj.pk)
    return '<a href="{}">{}</a>'.format(url, label)


# noinspection PyProtectedMember
def admin_view_reverse_fk_links(modeladmin: ModelAdmin,
                                obj,
                                reverse_fk_set_field: str,
                                missing: str = "(None)",
                                use_str: bool = True,
                                separator: str = "<br>",
                                view_type: str = "change",
                                current_app: str = None) -> str:
    """
    Get multiple Django admin site URL for multiple objects linked to our
    object of interest (where the other objects have foreign keys to our
    object).
    """
    if not hasattr(obj, reverse_fk_set_field):
        return missing
    linked_objs = getattr(obj, reverse_fk_set_field).all()
    if not linked_objs:
        return missing
    first = linked_objs[0]
    app_name = first._meta.app_label.lower()
    model_name = first._meta.object_name.lower()
    viewname = "admin:{}_{}_{}".format(app_name, model_name, view_type)
    if current_app is None:
        current_app = modeladmin.admin_site.name
    links = []
    for linked_obj in linked_objs:
        # log.debug("linked_obj: {}".format(linked_obj))
        url = reverse(viewname, args=[linked_obj.pk], current_app=current_app)

        if use_str:
            label = escape(str(linked_obj))
        else:
            label = "{} {}".format(escape(linked_obj._meta.object_name),
                                   linked_obj.pk)
        links.append('<a href="{}">{}</a>'.format(url, label))
    # log.debug("links: {}".format(links))
    return separator.join(links)
