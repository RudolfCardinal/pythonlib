#!/usr/bin/env python
# cardinal_pythonlib/rnc_web.py

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

**Support for web scripts.**

"""


import base64
import binascii
import cgi
import configparser
import dateutil.parser
import dateutil.tz
import datetime
import logging
import os
import re
# import six
import sys
from typing import (Any, Callable, Dict, Iterable, List, Optional,
                    Tuple, Union)

from cardinal_pythonlib.wsgi.constants import (
    TYPE_WSGI_APP_RESULT,
    TYPE_WSGI_START_RESPONSE,
    TYPE_WSGI_RESPONSE_HEADERS,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

WSGI_TUPLE_TYPE = Tuple[str, TYPE_WSGI_RESPONSE_HEADERS, bytes]
# ... contenttype, extraheaders, output

# =============================================================================
# Constants
# =============================================================================

_NEWLINE_REGEX = re.compile("\n", re.MULTILINE)
BASE64_PNG_URL_PREFIX = "data:image/png;base64,"
PNG_SIGNATURE_HEXSTRING = "89504E470D0A1A0A"
# ... http://en.wikipedia.org/wiki/Portable_Network_Graphics#Technical_details
PNG_SIGNATURE_HEX = binascii.unhexlify(PNG_SIGNATURE_HEXSTRING)
# ... bytes in Python 3; str in Python 2


# =============================================================================
# Misc
# =============================================================================

def print_utf8(s: str) -> None:
    """
    Writes a Unicode string to ``sys.stdout`` in UTF-8 encoding.
    """
    sys.stdout.write(s.encode('utf-8'))


def get_int_or_none(s: str) -> Optional[int]:
    """
    Returns the integer value of a string, or ``None`` if it's not convertible
    to an ``int``.
    """
    try:
        return int(s)
        # int(x) will return something of type long if it's a big number,
        # but happily
    except (TypeError, ValueError):
        return None


def get_float_or_none(s: str) -> Optional[float]:
    """
    Returns the float value of a string, or ``None`` if it's not convertible
    to a ``float``.
    """
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def is_1(s: str) -> bool:
    """
    ``True`` if the input is the string literal ``"1"``, otherwise ``False``.
    """
    return True if s == "1" else False


def number_to_dp(number: Optional[float],
                 dp: int,
                 default: Optional[str] = "",
                 en_dash_for_minus: bool = True) -> str:
    """
    Format number to ``dp`` decimal places, optionally using a UTF-8 en dash
    for minus signs.
    """
    if number is None:
        return default
    if number == float("inf"):
        return u"∞"
    if number == float("-inf"):
        s = u"-∞"
    else:
        s = u"{:.{precision}f}".format(number, precision=dp)
    if en_dash_for_minus:
        s = s.replace("-", u"–")  # hyphen becomes en dash for minus sign
    return s


# =============================================================================
# CGI
# =============================================================================

def debug_form_contents(form: cgi.FieldStorage,
                        to_stderr: bool = True,
                        to_logger: bool = False) -> None:
    """
    Writes the keys and values of a CGI form to ``stderr``.
    """
    for k in form.keys():
        text = "{0} = {1}".format(k, form.getvalue(k))
        if to_stderr:
            sys.stderr.write(text)
        if to_logger:
            log.info(text)
    # But note also: cgi.print_form(form)


def cgi_method_is_post(environ: Dict[str, str]) -> bool:
    """
    Determines if the CGI method was ``POST``, given the CGI environment.
    """
    method = environ.get("REQUEST_METHOD", None)
    if not method:
        return False
    return method.upper() == "POST"


def get_cgi_parameter_str(form: cgi.FieldStorage,
                          key: str,
                          default: str = None) -> str:
    """
    Extracts a string parameter from a CGI form.
    Note: ``key`` is CASE-SENSITIVE.
    """
    paramlist = form.getlist(key)
    if len(paramlist) == 0:
        return default
    return paramlist[0]


def get_cgi_parameter_str_or_none(form: cgi.FieldStorage,
                                  key: str) -> Optional[str]:
    """
    Extracts a string parameter from a CGI form, or ``None`` if the key doesn't
    exist or the string is zero-length.
    """
    s = get_cgi_parameter_str(form, key)
    if s is None or len(s) == 0:
        return None
    return s


def get_cgi_parameter_list(form: cgi.FieldStorage, key: str) -> List[str]:
    """
    Extracts a list of values, all with the same key, from a CGI form.
    """
    return form.getlist(key)


def get_cgi_parameter_bool(form: cgi.FieldStorage, key: str) -> bool:
    """
    Extracts a boolean parameter from a CGI form, on the assumption that
    ``"1"`` is ``True`` and everything else is ``False``.
    """
    return is_1(get_cgi_parameter_str(form, key))


def get_cgi_parameter_bool_or_default(form: cgi.FieldStorage,
                                      key: str,
                                      default: bool = None) -> Optional[bool]:
    """
    Extracts a boolean parameter from a CGI form (``"1"`` = ``True``,
    other string = ``False``, absent/zero-length string = default value).
    """
    s = get_cgi_parameter_str(form, key)
    if s is None or len(s) == 0:
        return default
    return is_1(s)


def get_cgi_parameter_bool_or_none(form: cgi.FieldStorage,
                                   key: str) -> Optional[bool]:
    """
    Extracts a boolean parameter from a CGI form (``"1"`` = ``True``,
    other string = False, absent/zero-length string = ``None``).
    """
    return get_cgi_parameter_bool_or_default(form, key, default=None)


def get_cgi_parameter_int(form: cgi.FieldStorage, key: str) -> Optional[int]:
    """
    Extracts an integer parameter from a CGI form, or ``None`` if the key is
    absent or the string value is not convertible to ``int``.
    """
    return get_int_or_none(get_cgi_parameter_str(form, key))


def get_cgi_parameter_float(form: cgi.FieldStorage,
                            key: str) -> Optional[float]:
    """
    Extracts a float parameter from a CGI form, or None if the key is
    absent or the string value is not convertible to ``float``.
    """
    return get_float_or_none(get_cgi_parameter_str(form, key))


def get_cgi_parameter_datetime(form: cgi.FieldStorage,
                               key: str) -> Optional[datetime.datetime]:
    """
    Extracts a date/time parameter from a CGI form. Applies the LOCAL
    timezone if none specified.
    """
    try:
        s = get_cgi_parameter_str(form, key)
        if not s:
            # if you dateutil.parser.parse() an empty string,
            # you get today's date
            return None
        d = dateutil.parser.parse(s)
        if d.tzinfo is None:  # as it will be
            d = d.replace(tzinfo=dateutil.tz.tzlocal())
        return d
    except ValueError:
        return None


def get_cgi_parameter_file(form: cgi.FieldStorage,
                           key: str) -> Optional[bytes]:
    """
    Extracts a file's contents from a "file" input in a CGI form, or None
    if no such file was uploaded.
    """
    (filename, filecontents) = get_cgi_parameter_filename_and_file(form, key)
    return filecontents


def get_cgi_parameter_filename_and_file(form: cgi.FieldStorage, key: str) \
        -> Tuple[Optional[str], Optional[bytes]]:
    """
    Extracts a file's name and contents from a "file" input in a CGI form.
    Returns ``(name, contents)``, or ``(None, None)`` if no such file was
    uploaded.
    """
    if not (key in form):
        log.warning('get_cgi_parameter_file: form has no key {}'.format(key))
        return None, None
    fileitem = form[key]  # a nested FieldStorage instance; see
    # http://docs.python.org/2/library/cgi.html#using-the-cgi-module
    if isinstance(fileitem, cgi.MiniFieldStorage):
        log.warning('get_cgi_parameter_file: MiniFieldStorage found - did you '
                    'forget to set enctype="multipart/form-data" in '
                    'your form?')
        return None, None
    if not isinstance(fileitem, cgi.FieldStorage):
        log.warning('get_cgi_parameter_file: no FieldStorage instance with '
                    'key {} found'.format(key))
        return None, None
    if fileitem.filename and fileitem.file:  # can check "file" or "filename"
        return fileitem.filename, fileitem.file.read()
        # as per
        # http://upsilon.cc/~zack/teaching/0607/techweb/02-python-cgi.pdf
        # Alternative:
        # return get_cgi_parameter_str(form, key) # contents of the file
    # Otherwise, information about problems:
    if not fileitem.file:
        log.warning('get_cgi_parameter_file: fileitem has no file')
    elif not fileitem.filename:
        log.warning('get_cgi_parameter_file: fileitem has no filename')
    else:
        log.warning('get_cgi_parameter_file: unknown failure reason')
    return None, None

    # "If a field represents an uploaded file, accessing the value
    # via the value attribute or the getvalue() method reads the
    # entire file in memory as a string. This may not be what you
    # want. You can test for an uploaded file by testing either
    # the filename attribute or the file attribute. You can then
    # read the data at leisure from the file attribute:"


def cgi_parameter_exists(form: cgi.FieldStorage, key: str) -> bool:
    """
    Does a CGI form contain the key?
    """
    s = get_cgi_parameter_str(form, key)
    return s is not None


def checkbox_checked(b: Any) -> str:
    """
    Returns ``' checked="checked"'`` if ``b`` is true; otherwise ``''``.

    Use this code to fill the ``{}`` in e.g.:
    
    .. code-block:: none

        <label>
            <input type="checkbox" name="myfield" value="1"{}>
            This will be pre-ticked if you insert " checked" where the braces
            are. The newer, more stringent requirement is ' checked="checked"'.
        </label>
    """
    return ' checked="checked"' if b else ''


def option_selected(variable: Any, testvalue: Any) -> str:
    """
    Returns ``' selected="selected"'`` if ``variable == testvalue`` else
    ``''``; for use with HTML select options.
    """
    return ' selected="selected"' if variable == testvalue else ''


# =============================================================================
# Environment
# =============================================================================

def getenv_escaped(key: str, default: str = None) -> Optional[str]:
    """
    Returns an environment variable's value, CGI-escaped, or ``None``.
    """
    value = os.getenv(key, default)
    # noinspection PyDeprecation
    return cgi.escape(value) if value is not None else None


def getconfigvar_escaped(config: configparser.ConfigParser,
                         section: str,
                         key: str) -> Optional[str]:
    """
    Returns a CGI-escaped version of the value read from an INI file using
    :class:`ConfigParser`, or ``None``.
    """
    value = config.get(section, key)
    # noinspection PyDeprecation
    return cgi.escape(value) if value is not None else None


def get_cgi_fieldstorage_from_wsgi_env(
        env: Dict[str, str],
        include_query_string: bool = True) -> cgi.FieldStorage:
    """
    Returns a :class:`cgi.FieldStorage` object from the WSGI environment.
    """
    # http://stackoverflow.com/questions/530526/accessing-post-data-from-wsgi
    post_env = env.copy()
    if not include_query_string:
        post_env['QUERY_STRING'] = ''
    form = cgi.FieldStorage(
        fp=env['wsgi.input'],
        environ=post_env,
        keep_blank_values=True
    )
    return form


# =============================================================================
# Blobs, pictures...
# =============================================================================

def is_valid_png(blob: Optional[bytes]) -> bool:
    """
    Does a blob have a valid PNG signature?
    """
    if not blob:
        return False
    return blob[:8] == PNG_SIGNATURE_HEX


def get_png_data_url(blob: Optional[bytes]) -> str:
    """
    Converts a PNG blob into a local URL encapsulating the PNG.
    """
    return BASE64_PNG_URL_PREFIX + base64.b64encode(blob).decode('ascii')


def get_png_img_html(blob: Union[bytes, memoryview],
                     extra_html_class: str = None) -> str:
    """
    Converts a PNG blob to an HTML IMG tag with embedded data.
    """
    return """<img {}src="{}" />""".format(
        'class="{}" '.format(extra_html_class) if extra_html_class else "",
        get_png_data_url(blob)
    )


# =============================================================================
# HTTP results
# =============================================================================

# Also, filenames:
#   http://stackoverflow.com/questions/151079
#   http://greenbytes.de/tech/tc2231/#inlwithasciifilenamepdf

def pdf_result(pdf_binary: bytes,
               extraheaders: TYPE_WSGI_RESPONSE_HEADERS = None,
               filename: str = None) -> WSGI_TUPLE_TYPE:
    """
    Returns ``(contenttype, extraheaders, data)`` tuple for a PDF.
    """
    extraheaders = extraheaders or []
    if filename:
        extraheaders.append(
            ('content-disposition', 'inline; filename="{}"'.format(filename))
        )
    contenttype = 'application/pdf'
    if filename:
        contenttype += '; filename="{}"'.format(filename)
    # log.debug("type(pdf_binary): {}".format(type(pdf_binary)))
    return contenttype, extraheaders, pdf_binary


def zip_result(zip_binary: bytes,
               extraheaders: TYPE_WSGI_RESPONSE_HEADERS = None,
               filename: str = None) -> WSGI_TUPLE_TYPE:
    """
    Returns ``(contenttype, extraheaders, data)`` tuple for a ZIP.
    """
    extraheaders = extraheaders or []
    if filename:
        extraheaders.append(
            ('content-disposition', 'inline; filename="{}"'.format(filename))
        )
    contenttype = 'application/zip'
    if filename:
        contenttype += '; filename="{}"'.format(filename)
    return contenttype, extraheaders, zip_binary


def html_result(html: str,
                extraheaders: TYPE_WSGI_RESPONSE_HEADERS = None) \
        -> WSGI_TUPLE_TYPE:
    """
    Returns ``(contenttype, extraheaders, data)`` tuple for UTF-8 HTML.
    """
    extraheaders = extraheaders or []
    return 'text/html; charset=utf-8', extraheaders, html.encode("utf-8")


def xml_result(xml: str,
               extraheaders: TYPE_WSGI_RESPONSE_HEADERS = None) \
        -> WSGI_TUPLE_TYPE:
    """
    Returns ``(contenttype, extraheaders, data)`` tuple for UTF-8 XML.
    """
    extraheaders = extraheaders or []
    return 'text/xml; charset=utf-8', extraheaders, xml.encode("utf-8")


def text_result(text: str,
                extraheaders: TYPE_WSGI_RESPONSE_HEADERS = None,
                filename: str = None) -> WSGI_TUPLE_TYPE:
    """
    Returns ``(contenttype, extraheaders, data)`` tuple for UTF-8 text.
    """
    extraheaders = extraheaders or []
    if filename:
        extraheaders.append(
            ('content-disposition', 'inline; filename="{}"'.format(filename))
        )
    contenttype = 'text/plain; charset=utf-8'
    if filename:
        contenttype += '; filename="{}"'.format(filename)
    return contenttype, extraheaders, text.encode("utf-8")


def tsv_result(text: str,
               extraheaders: TYPE_WSGI_RESPONSE_HEADERS = None,
               filename: str = None) -> WSGI_TUPLE_TYPE:
    """
    Returns ``(contenttype, extraheaders, data)`` tuple for UTF-8 TSV.
    """
    extraheaders = extraheaders or []
    if filename:
        extraheaders.append(
            ('content-disposition', 'inline; filename="{}"'.format(filename))
        )
    contenttype = 'text/tab-separated-values; charset=utf-8'
    if filename:
        contenttype += '; filename="{}"'.format(filename)
    return contenttype, extraheaders, text.encode("utf-8")


# =============================================================================
# CGI
# =============================================================================

def print_result_for_plain_cgi_script_from_tuple(
        contenttype_headers_content: WSGI_TUPLE_TYPE,
        status: str = '200 OK') -> None:
    """
    Writes HTTP result to stdout.

    Args:
        contenttype_headers_content:
            the tuple ``(contenttype, extraheaders, data)``
        status:
            HTTP status message (default ``"200 OK``)
    """
    contenttype, headers, content = contenttype_headers_content
    print_result_for_plain_cgi_script(contenttype, headers, content, status)


def print_result_for_plain_cgi_script(contenttype: str,
                                      headers: TYPE_WSGI_RESPONSE_HEADERS,
                                      content: bytes,
                                      status: str = '200 OK') -> None:
    """
    Writes HTTP request result to stdout.
    """
    headers = [
        ("Status", status),
        ("Content-Type", contenttype),
        ("Content-Length", str(len(content))),
    ] + headers
    sys.stdout.write("\n".join([h[0] + ": " + h[1] for h in headers]) + "\n\n")
    sys.stdout.write(content)


# =============================================================================
# WSGI
# =============================================================================

def wsgi_simple_responder(
        result: Union[str, bytes],
        handler: Callable[[Union[str, bytes]], WSGI_TUPLE_TYPE],
        start_response: TYPE_WSGI_START_RESPONSE,
        status: str = '200 OK',
        extraheaders: TYPE_WSGI_RESPONSE_HEADERS = None) \
        -> TYPE_WSGI_APP_RESULT:
    """
    Simple WSGI app.

    Args:
        result: the data to be processed by ``handler``
        handler: a function returning a ``(contenttype, extraheaders, data)``
            tuple, e.g. ``text_result``, ``html_result``
        start_response: standard WSGI ``start_response`` function
        status: status code (default ``"200 OK"``)
        extraheaders: optional extra HTTP headers

    Returns:
        WSGI application result

    """
    extraheaders = extraheaders or []
    (contenttype, extraheaders2, output) = handler(result)
    response_headers = [('Content-Type', contenttype),
                        ('Content-Length', str(len(output)))]
    response_headers.extend(extraheaders)
    if extraheaders2 is not None:
        response_headers.extend(extraheaders2)
    # noinspection PyArgumentList
    start_response(status, response_headers)
    return [output]


# =============================================================================
# HTML
# =============================================================================

def webify(v: Any, preserve_newlines: bool = True) -> str:
    """
    Converts a value into an HTML-safe ``str`` (formerly, in Python 2:
    ``unicode``).

    Converts value ``v`` to a string; escapes it to be safe in HTML
    format (escaping ampersands, replacing newlines with ``<br>``, etc.).
    Returns ``""`` for blank input.
    """
    nl = "<br>" if preserve_newlines else " "
    if v is None:
        return ""
    if not isinstance(v, str):
        v = str(v)
    # noinspection PyDeprecation
    return cgi.escape(v).replace("\n", nl).replace("\\n", nl)


def websafe(value: str) -> str:
    """
    Makes a string safe for inclusion in ASCII-encoded HTML.
    """
    # noinspection PyDeprecation
    return cgi.escape(value).encode('ascii', 'xmlcharrefreplace')
    # http://stackoverflow.com/questions/1061697


def replace_nl_with_html_br(string: str) -> str:
    """
    Replaces newlines with ``<br>``.
    """
    return _NEWLINE_REGEX.sub("<br>", string)


def bold_if_not_blank(x: Optional[str]) -> str:
    """
    HTML-emboldens content, unless blank.
    """
    if x is None:
        return u"{}".format(x)
    return u"<b>{}</b>".format(x)


def make_urls_hyperlinks(text: str) -> str:
    """
    Adds hyperlinks to text that appears to contain URLs.

    See

    - http://stackoverflow.com/questions/1071191

      - ... except that double-replaces everything; e.g. try with
        ``text = "me@somewhere.com me@somewhere.com"``

    - http://stackp.online.fr/?p=19
    """
    find_url = r'''
        (?x)(              # verbose identify URLs within text
        (http|ftp|gopher)  # make sure we find a resource type
        ://                # ...needs to be followed by colon-slash-slash
        (\w+[:.]?){2,}     # at least two domain groups, e.g. (gnosis.)(cx)
        (/?|               # could be just the domain name (maybe w/ slash)
        [^ \n\r"]+         # or stuff then space, newline, tab, quote
        [\w/])             # resource name ends in alphanumeric or slash
        (?=[\s\.,>)'"\]])  # assert: followed by white or clause ending
        )                  # end of match group
    '''
    replace_url = r'<a href="\1">\1</a>'
    find_email = re.compile('([.\w\-]+@(\w[\w\-]+\.)+[\w\-]+)')
    # '.' doesn't need escaping inside square brackets
    # https://stackoverflow.com/questions/10397968/escape-dot-in-a-regex-range
    replace_email = r'<a href="mailto:\1">\1</a>'
    text = re.sub(find_url, replace_url, text)
    text = re.sub(find_email, replace_email, text)
    return text


def html_table_from_query(rows: Iterable[Iterable[Optional[str]]],
                          descriptions: Iterable[Optional[str]]) -> str:
    """
    Converts rows from an SQL query result to an HTML table.
    Suitable for processing output from the defunct function
    ``rnc_db.fetchall_with_fieldnames(sql)``.
    """
    html = u"<table>\n"

    # Header row
    html += u"<tr>"
    for x in descriptions:
        if x is None:
            x = u""
        html += u"<th>{}</th>".format(webify(x))
    html += u"</tr>\n"

    # Data rows
    for row in rows:
        html += u"<tr>"
        for x in row:
            if x is None:
                x = u""
            html += u"<td>{}</td>".format(webify(x))
        html += u"<tr>\n"

    html += u"</table>\n"
    return html
