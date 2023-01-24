#!/usr/bin/env python
# cardinal_pythonlib/spreadsheets.py

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

**Manipulate spreadsheets.**

Note:

- openpyxl is dreadfully slow. Its results are picklable, but not sensibly so
  (e.g. generating a >500Mb picklefile from a 12Mb spreadsheet.
- xlrd is much faster, but we can't pickle its results.

"""

import datetime
import decimal
from decimal import Decimal
import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from cardinal_pythonlib.datetimefunc import (
    coerce_to_pendulum,
    pendulum_to_datetime_stripping_tz,
)
from cardinal_pythonlib.progress import ActivityCounter
from cardinal_pythonlib.reprfunc import simple_repr

try:
    # noinspection PyPackageRequirements
    import xlrd

    # noinspection PyPackageRequirements
    from xlrd import Book

    # noinspection PyPackageRequirements
    from xlrd.sheet import Cell, Sheet
except ImportError:
    raise ImportError("You must install the 'xlrd' package.")

log = logging.getLogger(__name__)


# =============================================================================
# Consistency checks
# =============================================================================


def all_same(items: Iterable[Any]) -> bool:
    """
    Are all the items the same?

    https://stackoverflow.com/questions/3787908/python-determine-if-all-items-of-a-list-are-the-same-item

    ... though we will also allow "no items" to pass the test.
    """  # noqa
    return len(set(items)) <= 1


def values_by_attr(items: Sequence[Any], attr: str) -> List[Any]:
    """
    Returns the values of a given attribute for each of the ``items``.

    Args:
        items:
            Items to check
        attr:
            Name of attribute whose value should be taken across items.
    """
    return [getattr(item, attr) for item in items]


def attr_all_same(items: Sequence[Any], attr: str) -> bool:
    """
    Returns whether the value of an attribute is the same across a collection
    of items.

    Args:
        items:
            Items to check
        attr:
            Name of attribute whose value should be compared across items.
    """
    return all_same(values_by_attr(items, attr))


def check_attr_all_same(
    items: Sequence[Any],
    attr: str,
    id_attr: str = None,
    fail_if_different: bool = True,
    ignore_none: bool = False,
) -> None:
    """
    Checks if the value of an attribute is the same across a collection of
    items, and takes some action if not.

    Args:
        items:
            Items to check
        attr:
            Name of attribute whose value should be compared across items.
        id_attr:
            If the attributes are not all the same, use the value of this
            attribute from the first item to give some identifying context
            to the failure message.
        fail_if_different:
            If true, raises :exc:`ValueError` on failure; otherwise, prints a
            warning to the log.
        ignore_none:
            Ignore ``None`` values?
    """
    values = values_by_attr(items, attr)
    if ignore_none:
        values = [v for v in values if v is not None]
    if all_same(values):
        return
    # The rest of this function is about producing an error or a warning.
    first_item = items[0]
    if id_attr:
        identity = f"For {id_attr}={getattr(first_item, id_attr)!r}, "
    else:
        identity = ""
    msg = f"{identity}attribute {attr} is inconsistent: {values}"
    if fail_if_different:
        raise ValueError(msg)
    else:
        log.warning(msg)


def require_attr_all_same(
    items: Sequence[Any], attr: str, id_attr: str, ignore_none: bool = False
) -> None:
    """
    Raise if the ``attr`` attribute of each item in ``items`` is not the same.
    See :func:`check_attr_all_same`.
    """
    check_attr_all_same(
        items, attr, id_attr, fail_if_different=True, ignore_none=ignore_none
    )


def prefer_attr_all_same(
    items: Sequence[Any], attr: str, id_attr: str, ignore_none: bool = False
) -> None:
    """
    Warn if the ``attr`` attribute of each item in ``items`` is not the same.
    See :func:`check_attr_all_same`.
    """
    check_attr_all_same(
        items, attr, id_attr, fail_if_different=False, ignore_none=ignore_none
    )


# =============================================================================
# Spreadsheet operations: xlrd
# =============================================================================


def load_workbook(spreadsheet_filename: str) -> Book:
    """
    Load a workbook.
    """
    # Pickling creates massive files; skip it
    log.info(f"Loading: {spreadsheet_filename!r}...")
    book = xlrd.open_workbook(
        filename=spreadsheet_filename,
        on_demand=True,  # may affect rather little, but we can try
    )
    log.info("... done")
    return book


def read_value_row(row: Sequence[Cell], colnum: int) -> Any:
    """
    Retrieves a value from a cell of a spreadsheet, given a row.

    AVOID: slower than index access (see :class:`SheetHolder`,
    :class:`RowHolder`).
    """
    return row[colnum].value


def read_int_row(row: Sequence[Cell], colnum: int) -> Optional[int]:
    """
    Reads an integer from a spreadsheet, given a row.

    AVOID: slower than index access (see :class:`SheetHolder`,
    :class:`RowHolder`).
    """
    v = read_value_row(row, colnum)
    if v is None:
        return None
    return int(v)


# =============================================================================
# Helper functions
# =============================================================================


def none_or_blank_string(x: Any) -> bool:
    """
    Is ``x`` either ``None`` or a string that is empty or contains nothing but
    whitespace?
    """
    if x is None:
        return True
    elif isinstance(x, str) and not x.strip():
        return True
    else:
        return False


def column_lettering(colnum: int) -> str:
    """
    Converts a zero-based column index into a spreadsheet-style column name
    (A[0] to Z[25], then AA[26] to AZ[51], etc). Basically, it's almost base
    26, but without a proper sense of zero (in that A is zero, but AA is 26).
    """
    assert colnum >= 0
    base = 26
    zero_char = ord("A")
    reversed_chars = ""
    while True:
        big, small = divmod(colnum, base)
        reversed_chars += chr(zero_char + small)
        if big == 0:
            break
        colnum = big - 1
    return reversed_chars[::-1]  # reverse again to get the final answer


def colnum_zb_from_alphacol(alphacol: str) -> int:
    """
    Reverses :func:`column_lettering`, generating a zero-based column index
    from an alphabetical name (A to Z, AA to AZ, etc.).
    """
    base = 26
    zero_char = ord("A")
    total = 0
    reversed_chars = alphacol[::-1]
    for pos, char in enumerate(reversed_chars):
        digit_value = ord(char) - zero_char  # e.g. 0 for A, 25 for Z
        assert 0 <= digit_value < base
        if pos > 0:
            digit_value += 1
        total += digit_value * pow(base, pos)
    return total


# =============================================================================
# SheetHolder
# =============================================================================


class SheetHolder(object):
    """
    Class to read from an Excel spreadsheet.
    """

    SHEET_NAME = ""  # may be overridden
    HEADER_ROW_ZERO_BASED = 0  # 0 is the first row (usually a header row)
    FIRST_DATA_ROW_ZERO_BASED = 1
    NULL_VALUES = [None, ""]

    BOOL_TRUE_VALUES_LOWERCASE = [1, "t", "true", "y", "yes"]
    BOOL_FALSE_VALUES_LOWERCASE = [0, "f", "false", "n", "no"]
    BOOL_UNKNOWN_VALUES_LOWERCASE = [None, "", "?", "not known", "unknown"]

    def __init__(
        self,
        book: Book = None,
        sheet_name: str = None,
        sheet_index: int = None,
        sheet: Sheet = None,
        header_row_zero_based: int = None,
        first_data_row_zero_based: int = None,
        null_values: List[Any] = None,
        bool_true_values_lowercase: List[Any] = None,
        bool_false_values_lowercase: List[Any] = None,
        bool_unknown_values_lowercase: List[Any] = None,
        debug_max_rows_per_sheet: int = None,
    ) -> None:
        """
        There are two ways to specify the sheet:

        1.  Provide a workbook via ``book`` and...

            (a) a sheet number, or
            (b) a sheet name.

        2.  Provide a worksheet directly via ``sheet``.

        You can specify the following as ``_init__`` parameters or (via their
        capitalized versions) by subclassing:

        - sheet_name
        - header_row_zero_based
        - null_values
        - bool_true_values_lowercase
        - bool_false_values_lowercase
        - bool_unknown_values_lowercase

        Initialization parameters take priority over subclassed values.

        Args:
            book:
                Workbook, from which a worksheet should be selected.
            sheet_name:
                Name of a sheet to select from within ``book``.
            sheet_index:
                Index (zero-based) of a sheet to select from within ``book``.
            sheet:
                Worksheet, provided directly.
            header_row_zero_based:
                Row number (zero-based) of the header row.
            first_data_row_zero_based:
                Row number (zero-based) of the first row containing data.
            null_values:
                Values to treat as null (blank) values, converted to Python
                ``None``.
            bool_true_values_lowercase:
                Values to treat, by default, as ``True`` in Boolean columns.
            bool_false_values_lowercase:
                Values to treat, by default, as ``False`` in Boolean columns.
            bool_unknown_values_lowercase:
                Values to treat, by default, as missing/unknown in Boolean
                columns.
            debug_max_rows_per_sheet:
                Debugging option: the maximum number of data rows to
                process.
        """

        # Establish worksheet
        if book:
            assert sheet is None, (
                f"You specified 'book', so must not specify 'sheet', but "
                f"'sheet' was specified as: {sheet!r}"
            )
            if sheet_index is not None:
                self.sheet = book.sheet_by_index(sheet_index)
                self.sheet_description = (
                    f"book={book!r}, sheet_index={sheet_index!r}"
                )
            else:
                sheet_name = sheet_name or self.SHEET_NAME
                assert sheet_name, "Provide sheet_name or override SHEET_NAME"
                self.sheet = book.sheet_by_name(sheet_name)
                self.sheet_description = (
                    f"book={book!r}, sheet_name={sheet_name!r}"
                )
        else:
            assert sheet is not None, (
                "You didn't specify 'book', so must specify 'sheet', but it "
                "was None"
            )
            self.sheet = sheet
            self.sheet_description = f"sheet={sheet!r}"

        # Other parameters
        self.header_row_zero_based = (
            header_row_zero_based
            if header_row_zero_based is not None
            else self.HEADER_ROW_ZERO_BASED
        )
        self.first_data_row_zero_based = (
            first_data_row_zero_based
            if first_data_row_zero_based is not None
            else self.FIRST_DATA_ROW_ZERO_BASED
        )
        self.null_values = (
            null_values if null_values is not None else self.NULL_VALUES
        )
        self.bool_true_values_lowercase = (
            bool_true_values_lowercase
            if bool_true_values_lowercase is not None
            else self.BOOL_TRUE_VALUES_LOWERCASE
        )
        self.bool_false_values_lowercase = (
            bool_false_values_lowercase
            if bool_false_values_lowercase is not None
            else self.BOOL_FALSE_VALUES_LOWERCASE
        )
        self.bool_unknown_values_lowercase = (
            bool_unknown_values_lowercase
            if bool_unknown_values_lowercase is not None
            else self.BOOL_UNKNOWN_VALUES_LOWERCASE
        )
        self.debug_max_rows_per_sheet = debug_max_rows_per_sheet

        # Establish workbook
        self.book = self.sheet.book

        # Cached information
        self._headings = None  # type: Optional[List[str]]
        self._checked_headers = {}  # type: Dict[int, str]

    # -------------------------------------------------------------------------
    # Information
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        return (
            f"<Sheet {self.sheet_name!r}, specifed as "
            f"{self.sheet_description}>"
        )

    @property
    def n_rows(self) -> int:
        """
        Total number of rows.
        """
        return self.sheet.nrows

    @property
    def n_data_rows(self) -> int:
        """
        Total number of data rows (below any header row).
        """
        return self.n_rows - self.first_data_row_zero_based

    @property
    def sheet_name(self) -> str:
        """
        Name of the sheet within the workbook (file).
        """
        return self.sheet.name

    @property
    def headers(self) -> List[str]:
        """
        Returns all headings.
        """
        if self._headings is None:
            self._headings = [
                str(cell.value)
                for cell in self.sheet.row(self.header_row_zero_based)
            ]
        return self._headings

    @property
    def headings(self) -> List[str]:
        """
        Synonym for :data:`headers`.
        """
        return self.headers

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def _locinfo(self, row: int, col: int) -> str:
        """
        Location info for a cell, for errors.

        Args:
            row: zero-based row index
            col: zero-based column index
        """
        return (
            f" [sheet_name={self.sheet_name!r}, "
            f"row(1-based)={row+1}, "
            f"column(1-based)={col+1} ({column_lettering(col)})]"
        )

    def ensure_header(
        self, col: int, header: Union[str, Sequence[str]]
    ) -> None:
        """
        Ensures that the header is correct for a specified column, or raise
        :exc:`ValueError`.

        You can specify a single correct heading or a sequence (e.g. list)
        of them.
        """
        if col in self._checked_headers:
            # Already checked.
            return
        headers = self.headers
        if col < 0 or col >= len(headers):
            max_col_idx = len(headers) - 1
            raise ValueError(
                f"Bad column index {col} ({column_lettering(col)}); "
                f"possible range is 0-{max_col_idx} (columns "
                f"{column_lettering(0)}-{column_lettering(max_col_idx)})"
            )
        v = headers[col]  # observed value
        self._checked_headers[col] = v  # cache for subsquent check
        if isinstance(header, str):  # single valid header
            if v == header:
                return  # good
        else:  # multiple values are OK
            if v in header:
                return  # good
        raise ValueError(
            f"Bad header: should be {header!r}, but was {v!r}"
            + self._locinfo(self.header_row_zero_based, col)
        )

    def ensure_heading(
        self, col: int, heading: Union[str, Sequence[str]]
    ) -> None:
        """
        Synonym for :meth:`ensure_header`.
        """
        return self.ensure_header(col, heading)

    # -------------------------------------------------------------------------
    # Reading
    # -------------------------------------------------------------------------

    def read_value(
        self,
        row: int,
        col: int,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Any:
        """
        Retrieves a value from a cell of a spreadsheet.

        Optionally, check that the heading for this column is correct (see
        :meth:`ensure_header`).
        """
        if check_header is not None:
            try:
                self.ensure_header(col, check_header)
            except ValueError as e:
                raise ValueError(
                    f"When reading row with zero-based index {row}: {e}"
                )
        v = self.sheet.cell_value(row, col)
        if v in self.null_values:
            return None
        return v

    def read_datetime(
        self,
        row: int,
        col: int,
        default: datetime.datetime = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[datetime.datetime]:
        """
        Reads a datetime from an Excel spreadsheet via xlrd.

        https://stackoverflow.com/questions/32430679/how-to-read-dates-using-xlrd
        """  # noqa
        v = self.read_value(row, col, check_header=check_header)
        if none_or_blank_string(v):
            return default
        try:
            if isinstance(v, str):
                # Sometimes we get strings, like "1800-01-01". These are
                # outside the Excel range (1900 or 1904 onwards).
                p_datetime = coerce_to_pendulum(v)
                if p_datetime is None:
                    raise ValueError
                return pendulum_to_datetime_stripping_tz(p_datetime)
            else:
                # xlrd.xldate_as_tuple() converts an Excel number into a
                # tuple: (year, month, day, hour, minute, nearest_second)
                return datetime.datetime(
                    *xlrd.xldate_as_tuple(v, self.book.datemode)
                )
        except (TypeError, ValueError):
            raise ValueError(f"Bad date/time: {v!r}" + self._locinfo(row, col))

    def read_date(
        self,
        row: int,
        col: int,
        default: datetime.date = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[datetime.date]:
        """
        Reads a date from an Excel spreadsheet

        https://stackoverflow.com/questions/32430679/how-to-read-dates-using-xlrd
        """
        dt = self.read_datetime(row, col, check_header=check_header)
        if dt:
            return dt.date()
        return default

    def read_int(
        self,
        row: int,
        col: int,
        default: int = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[int]:
        """
        Reads an integer from a spreadsheet.
        """
        v = self.read_value(row, col, check_header=check_header)
        if none_or_blank_string(v):
            return default
        try:
            # - Now, the danger is that e.g. v == 7.6, which will cheerfully
            #   give int(v) == 7.
            # - [Note that int("7.6") will raise ValueError, whereas
            #   int(7.6) will succeed.]
            # - However, we want it to be an error to read a float/decimal as
            #   an integer accidentally, because otherwise we may lose data.
            # - Finally, sometimes str(v) is e.g. "92.0" when v is a perfectly
            #   valid integer, so we can't use 'if "." in str(v)' as a test.
            # - But comparing int(v) to float(v) works.
            iv = int(v)  # may raise
            if iv != float(v):  # this picks up non-integer values
                raise ValueError
            return iv
        except (TypeError, ValueError):
            raise ValueError(f"Bad int: {v!r}" + self._locinfo(row, col))

    def read_float(
        self,
        row: int,
        col: int,
        default: float = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[float]:
        """
        Reads a float from the spreadsheet.
        """
        v = self.read_value(row, col, check_header=check_header)
        if none_or_blank_string(v):
            return default
        try:
            return float(v)
        except (TypeError, ValueError):
            raise ValueError(f"Bad float: {v!r}" + self._locinfo(row, col))

    def read_decimal(
        self,
        row: int,
        col: int,
        default: Decimal = None,
        check_header: Union[str, Sequence[str]] = None,
        dp: int = None,
        rounding: str = decimal.ROUND_HALF_UP,
    ) -> Optional[Decimal]:
        """
        Reads a Decimal from the spreadsheet.

        If ``dp`` is not ``None``, force the result to a specified number of
        decimal places, using the specified rounding method.
        """
        v = self.read_value(row, col, check_header=check_header)
        if none_or_blank_string(v):
            return default
        try:
            x = Decimal(str(v))
            # ... better than Decimal(v), which converts e.g. 7.4 to
            # Decimal('7.4000000000000003552713678800500929355621337890625')
        except (TypeError, decimal.InvalidOperation):
            raise ValueError(f"Bad decimal: {v!r}" + self._locinfo(row, col))
        if dp is not None:
            nplaces = Decimal(10) ** (-dp)
            x = x.quantize(exp=nplaces, rounding=rounding)
        return x

    def read_str(
        self,
        row: int,
        col: int,
        default: str = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[str]:
        """
        Reads a string from a spreadsheet.
        """
        v = self.read_value(row, col, check_header=check_header)
        if none_or_blank_string(v):
            return default
        return str(v).strip()

    def read_str_int(
        self,
        row: int,
        col: int,
        default: str = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[str]:
        """
        Reads a string version of an integer. (This prevents e.g. "2" being
        read as a floating-point value of "2.0" then converted to a string.)
        """
        v_int = self.read_int(row, col, check_header=check_header)
        if v_int is None:
            return default
        return str(v_int)

    def read_str_nonfloat(
        self,
        row: int,
        col: int,
        default: str = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[str]:
        """
        Reads something that may be a string or numeric, but if it's numeric,
        it's integer (not float). (This prevents e.g. "2" being read as a
        floating-point value of "2.0" then converted to a string.)
        """
        v = self.read_value(row, col, check_header=check_header)
        if none_or_blank_string(v):
            return default
        # See read_int() for more on the logic used here.
        try:
            fv = float(v)  # may raise
        except (TypeError, ValueError):
            # Not numeric
            return v  # return the string version
        # If we get here, v is numeric (e.g. "7" or "6.5" or 3.5).
        try:
            iv = int(v)
        except (TypeError, ValueError):
            # Numeric, but not integer
            raise ValueError
        if iv != fv:  # this picks up non-integer values
            raise ValueError
        return str(iv)  # string version of int

    def read_bool(
        self,
        row: int,
        col: int,
        default: bool = None,
        true_values_lowercase: List[Any] = None,
        false_values_lowercase: List[Any] = None,
        unknown_values_lowercase: List[Any] = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[bool]:
        """
        Reads a boolean value.
        """
        if true_values_lowercase is None:
            true_values_lowercase = self.bool_true_values_lowercase
        if false_values_lowercase is None:
            false_values_lowercase = self.bool_false_values_lowercase
        if unknown_values_lowercase is None:
            unknown_values_lowercase = self.bool_unknown_values_lowercase
        raw_v = self.read_value(row, col, check_header=check_header)
        if none_or_blank_string(raw_v):
            v = None
        else:
            try:
                v = int(raw_v)
            except (TypeError, ValueError):
                v = str(raw_v).lower()
        if v in true_values_lowercase:
            return True
        elif v in false_values_lowercase:
            return False
        elif v in unknown_values_lowercase:
            return default
        else:
            raise ValueError(f"Bad bool: {raw_v!r}" + self._locinfo(row, col))

    def read_none(
        self,
        row: int,
        col: int,
        check_header: Union[str, Sequence[str]] = None,
    ) -> None:
        """
        Reads a value, and checks that it is a none/null value
        """
        v = self.read_value(row, col, check_header=check_header)
        if v is not None:
            raise ValueError(
                f"Value should be none/null but is {v!r}"
                + self._locinfo(row, col)
            )
        return None

    # -------------------------------------------------------------------------
    # Row generators
    # -------------------------------------------------------------------------

    def _setup_for_gen(
        self, with_counter: bool = True
    ) -> Tuple[int, Optional["ActivityCounter"]]:
        n_rows = self.sheet.nrows
        if with_counter:
            counter = ActivityCounter(
                activity="Reading row", n_total=self.n_data_rows
            )
        else:
            counter = None
        if self.debug_max_rows_per_sheet is not None:
            log.debug(
                f"Debug option: limiting to {self.debug_max_rows_per_sheet} "
                f"rows from spreadsheet {self}"
            )
            end = min(n_rows, self.debug_max_rows_per_sheet + 1)
        else:
            end = n_rows
        return end, counter

    def gen_row_numbers_excluding_header_row(
        self, with_counter: bool = True
    ) -> Iterable[int]:
        """
        Generates row numbers.

        xlrd uses 0-based numbering, so row 1 is the first beyond a header row.
        """
        end, counter = self._setup_for_gen(with_counter)
        for rownum in range(self.first_data_row_zero_based, end):
            if counter is not None:
                counter.tick()
            yield rownum

    def gen_rows_excluding_header_row(
        self, with_counter: bool = True
    ) -> Iterable[Sequence[Cell]]:
        """
        Generates rows. AVOID; index-based access is faster.

        xlrd uses 0-based numbering, so row 1 is the first beyond a header row.
        """
        end, counter = self._setup_for_gen(with_counter)
        for index in range(self.first_data_row_zero_based, end):
            if counter is not None:
                counter.tick()
            yield self.sheet.row(index)


# =============================================================================
# RowHolder
# =============================================================================


class RowHolder(object):
    """
    Class to read from a single row of a spreadsheet.

    The intended use is to create something like a dataclass, but one that
    knows its spreadsheet structure. Like this:

    .. code-block:: python

        from cardinal_pythonlib.spreadsheets import RowHolder, SheetHolder

        class ReferralSheetHolder(SheetHolder):
            SHEET_NAME = "Patient Referrals 2018-19"

            def gen_referral_rows(self) -> Iterable["ReferralRow"]:
                for rownum in self.gen_row_numbers_excluding_header_row():
                    yield ReferralRow(self, rownum)

        class ReferralRow(RowHolder):
            def __init__(self, sheetholder: SheetHolder, row: int) -> None:
                super().__init__(sheetholder, row)

                self.inc_next_col()  # column 0: query period; ignore
                self.patient_id = self.str_int_pp()
                self.referral_id_within_patient = self.int_pp()
                self.age_at_referral_int = self.int_pp()
                self.ethnicity = self.str_pp()
                self.gender = self.str_pp(check_header="Gender")

        def import_referrals(book: Book) -> None:
            sheet = ReferralSheetHolder(book)
            for referral in sheet.gen_referral_rows():
                pass  # do something useful here

    """

    def __init__(self, sheetholder: SheetHolder, row: int) -> None:
        self.sheetholder = sheetholder
        self.row = row  # zero-based index of our row
        self._next_col = (
            0  # zero-based column index of the next column to read  # noqa
        )

    # -------------------------------------------------------------------------
    # Information
    # -------------------------------------------------------------------------

    @property
    def sheet_name(self) -> str:
        return self.sheetholder.sheet_name

    def _get_relevant_attrs(self) -> List[str]:
        """
        Attributes added by the user, and row number.
        :return:
        """
        avoid = ["sheetholder", "row", "_next_col"]
        user_attrs = [k for k in self.__dict__.keys() if k not in avoid]
        attrs = ["sheet_name", "row"] + user_attrs
        return attrs

    def __str__(self) -> str:
        return simple_repr(self, self._get_relevant_attrs())

    def __repr__(self) -> str:
        return simple_repr(self, ["sheetholder", "row"])

    @property
    def row_zero_based(self) -> int:
        """
        Zero-based row number.
        """
        return self.row

    @property
    def row_one_based(self) -> int:
        """
        One-based row number.
        """
        return self.row + 1

    # -------------------------------------------------------------------------
    # Checks
    # -------------------------------------------------------------------------
    # More commonly, this is done via the "read...()" functions.

    def ensure_header(
        self, col: int, header: Union[str, Sequence[str]]
    ) -> None:
        """
        Ensures the column has an appropriate heading value, or raises
        :exc:`ValueError`.
        """
        self.sheetholder.ensure_header(col, header)

    def ensure_heading(
        self, col: int, header: Union[str, Sequence[str]]
    ) -> None:
        """
        Synonym for :meth:`ensure_header`.
        """
        self.ensure_header(col, header)

    # -------------------------------------------------------------------------
    # Read operations, given a column number
    # -------------------------------------------------------------------------
    # Compare equivalents in SheetHolder.

    def read_value(
        self, col: int, check_header: Union[str, Sequence[str]] = None
    ) -> Any:
        return self.sheetholder.read_value(
            self.row, col, check_header=check_header
        )

    def read_datetime(
        self,
        col: int,
        default: Any = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[datetime.date]:
        return self.sheetholder.read_datetime(
            self.row, col, default, check_header=check_header
        )

    def read_date(
        self,
        col: int,
        default: Any = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[datetime.date]:
        return self.sheetholder.read_date(
            self.row, col, default, check_header=check_header
        )

    def read_int(
        self,
        col: int,
        default: int = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[int]:
        return self.sheetholder.read_int(
            self.row, col, default, check_header=check_header
        )

    def read_float(
        self,
        col: int,
        default: float = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[float]:
        return self.sheetholder.read_float(
            self.row, col, default, check_header=check_header
        )

    def read_decimal(
        self,
        col: int,
        default: Decimal = None,
        check_header: Union[str, Sequence[str]] = None,
        dp: int = None,
        rounding: str = decimal.ROUND_HALF_UP,
    ) -> Optional[Decimal]:
        return self.sheetholder.read_decimal(
            self.row,
            col,
            default,
            check_header=check_header,
            dp=dp,
            rounding=rounding,
        )

    def read_str(
        self,
        col: int,
        default: str = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[str]:
        return self.sheetholder.read_str(
            self.row, col, default, check_header=check_header
        )

    def read_str_int(
        self,
        col: int,
        default: str = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[str]:
        return self.sheetholder.read_str_int(
            self.row, col, default, check_header=check_header
        )

    def read_str_nonfloat(
        self,
        col: int,
        default: str = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[str]:
        return self.sheetholder.read_str_nonfloat(
            self.row, col, default, check_header=check_header
        )

    def read_bool(
        self,
        col: int,
        default: bool = None,
        true_values_lowercase: List[Any] = None,
        false_values_lowercase: List[Any] = None,
        unknown_values_lowercase: List[Any] = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[bool]:
        return self.sheetholder.read_bool(
            row=self.row,
            col=col,
            default=default,
            true_values_lowercase=true_values_lowercase,
            false_values_lowercase=false_values_lowercase,
            unknown_values_lowercase=unknown_values_lowercase,
            check_header=check_header,
        )

    def read_none(
        self, col: int, check_header: Union[str, Sequence[str]] = None
    ) -> None:
        return self.sheetholder.read_none(
            row=self.row, col=col, check_header=check_header
        )

    # -------------------------------------------------------------------------
    # Check the next column
    # -------------------------------------------------------------------------

    def ensure_next_col_header(
        self, header: Union[str, Sequence[str]]
    ) -> None:
        """
        Ensures the next column has an appropriate heading value, or raises
        :exc:`ValueError`.
        """
        self.ensure_header(self._next_col, header)

    def ensure_next_col_heading(
        self, header: Union[str, Sequence[str]]
    ) -> None:
        """
        Synonym for :meth:`ensure_next_col_header`.
        """
        self.ensure_next_col_header(header)

    # -------------------------------------------------------------------------
    # Read operations, incrementing the next column number automatically.
    # -------------------------------------------------------------------------
    # "pp" for "++" post-increment, like C.

    @property
    def next_col(self) -> int:
        """
        Returns the column number (0-based) that will be used by the next
        automatic read operation.
        """
        return self._next_col

    def set_next_col(self, col: int) -> None:
        """
        Resets the next column to be read automatically.
        """
        self._next_col = col

    def inc_next_col(self) -> None:
        """
        Increments the next column to be read.
        """
        self._next_col += 1

    def value_pp(self, check_header: Union[str, Sequence[str]] = None) -> Any:
        """
        Reads a value, then increments the "current" column.
        Optionally, checks that the header for this column is as expected.
        """
        try:
            v = self.read_value(self._next_col, check_header=check_header)
        finally:
            self.inc_next_col()
        return v

    def datetime_pp(
        self,
        default: datetime.datetime = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[datetime.datetime]:
        """
        Reads a datetime, then increments the "current" column.
        Optionally, checks that the header for this column is as expected.
        """
        try:
            v = self.read_datetime(
                self._next_col, default, check_header=check_header
            )
        finally:
            self.inc_next_col()
        return v

    def date_pp(
        self,
        default: datetime.date = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[datetime.date]:
        """
        Reads a date, then increments the "current" column.
        Optionally, checks that the header for this column is as expected.
        """
        try:
            v = self.read_date(
                self._next_col, default, check_header=check_header
            )
        finally:
            self.inc_next_col()
        return v

    def int_pp(
        self,
        default: int = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[int]:
        """
        Reads an int, then increments the "current" column.
        Optionally, checks that the header for this column is as expected.
        """
        try:
            v = self.read_int(
                self._next_col, default, check_header=check_header
            )
        finally:
            self.inc_next_col()
        return v

    def float_pp(
        self,
        default: float = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[float]:
        """
        Reads a float, then increments the "current" column.
        Optionally, checks that the header for this column is as expected.
        """
        try:
            v = self.read_float(
                self._next_col, default, check_header=check_header
            )
        finally:
            self.inc_next_col()
        return v

    def decimal_pp(
        self,
        default: float = None,
        check_header: Union[str, Sequence[str]] = None,
        dp: int = None,
        rounding: str = decimal.ROUND_HALF_UP,
    ) -> Optional[Decimal]:
        """
        Reads a Decimal, then increments the "current" column.
        Optionally, checks that the header for this column is as expected.
        """
        try:
            v = self.read_decimal(
                self._next_col,
                default=default,
                check_header=check_header,
                dp=dp,
                rounding=rounding,
            )
        finally:
            self.inc_next_col()
        return v

    def str_pp(
        self,
        default: str = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[str]:
        """
        Reads a string, then increments the "current" column.
        Optionally, checks that the header for this column is as expected.
        """
        try:
            v = self.read_str(
                self._next_col, default, check_header=check_header
            )
        finally:
            self.inc_next_col()
        return v

    def str_int_pp(
        self,
        default: str = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[str]:
        """
        Reads an integer as a string, then increments the "current" column.
        Optionally, checks that the header for this column is as expected.
        """
        try:
            v = self.read_str_int(
                self._next_col, default, check_header=check_header
            )
        finally:
            self.inc_next_col()
        return v

    def str_nonfloat_pp(
        self,
        default: str = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[str]:
        """
        Reads something that may be a string or numeric, but if it's numeric,
        it's integer (not float). Then increments the "current" column.
        Optionally, checks that the header for this column is as expected.
        """
        try:
            v = self.read_str_nonfloat(
                self._next_col, default, check_header=check_header
            )
        finally:
            self.inc_next_col()
        return v

    def bool_pp(
        self,
        default: bool = None,
        true_values_lowercase: List[Any] = None,
        false_values_lowercase: List[Any] = None,
        unknown_values_lowercase: List[Any] = None,
        check_header: Union[str, Sequence[str]] = None,
    ) -> Optional[bool]:
        """
        Reads a boolean value, then increments the "current" column.
        Optionally, checks that the header for this column is as expected.
        """
        try:
            v = self.read_bool(
                col=self._next_col,
                default=default,
                true_values_lowercase=true_values_lowercase,
                false_values_lowercase=false_values_lowercase,
                unknown_values_lowercase=unknown_values_lowercase,
                check_header=check_header,
            )
        finally:
            self.inc_next_col()
        return v

    def none_pp(self, check_header: Union[str, Sequence[str]] = None) -> None:
        """
        Reads a null value, and ensures that it is null; then increments the
        "current" column. Optionally, checks that the header for this column is
        as expected.
        """
        try:
            self.read_none(col=self._next_col, check_header=check_header)
        finally:
            self.inc_next_col()
        return None
