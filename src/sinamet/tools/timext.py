from datetime import datetime, date, timedelta
from typing import overload

import pandas


def full_date_range(start, end, freq):
    """Return TimeSeries, with frequency"""
    _start_date = start
    _end_date = end  # END DATE INCLUDE IN TIME STEP !

    # Building list of dates
    # Nearest date (with freq) before start
    _startlistdates = pandas.date_range(end=_start_date,
                                        freq=freq,
                                        periods=1,
                                        closed='right')
    # Nearest date (with freq) after start
    _endlistdates = pandas.date_range(start=_end_date,
                                      freq=freq,
                                      periods=1,
                                      closed='left')
    # All dates in between
    _listdates = pandas.date_range(start=_start_date,
                                   end=_end_date,
                                   freq=freq)

    # print(_startlistdates)
    # print(_endlistdates)
    # print(_listdates)

    rslt = pandas.DatetimeIndex.union(_startlistdates, _listdates)
    rslt = pandas.DatetimeIndex.union(rslt, _endlistdates)
    return rslt

def common_nb_days(start1, end1, start2, end2):
    """End date excluded"""
    if start1 <= start2 and end1 >= end2:
        _return = (end2 - start2).days
    elif start2 <= start1 and end2 >= end1:
        _return = (end1 - start1).days
    elif end1 <= start2: # Period 1 before period 2
        _return = 0
    elif start1 >= end2:
        _return = 0
    elif start1 <= start2 and end1 <= end2:
        _return = (end1 - start2).days
    elif start1 >= start2 and end1 >= end2:
        _return = (end2 - start1).days
    else:
        raise ValueError("Unable to perform common_nb_days")
    #print(str(start1) + " -> " + str(end1) + " // " + \
    #      str(start2) + " -> " + str(end2) + " = " + str(_return))
    return _return


@overload
def to_date(d:  None) -> None: ...
@overload
def to_date(d: str | datetime | date) -> date: ...


def to_date(d: str | datetime | date | None) -> date | None:
    if d is None:
        return None

    if isinstance(d, str):
        try:
            return datetime.strptime(d, "%d/%m/%Y").date()
        except ValueError:
            try:
                return datetime.strptime(d, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(f"Invalid date format: '{date}'")
    elif isinstance(d, datetime):
        return d.date()
    elif isinstance(d, date):
        return d
    else:
        raise TypeError(f"Unknown date type: '{type(date)=}'")


def get_start_end_dates(start: str | datetime | date | None = None,
                        end: str | datetime | date | None = None,
                        year: int | str | None = None,
                        month: int | str | None = None
                        ) -> tuple[date, date]:
    """
        - start => start -- date.max
        - end => date.min -- end
        - start & end => start -- end
        - year => 01/01/year -- 12/31/year
        - year & month => 01/month/year -- 01/month+1/year - 1
        - no infos => date.min -- date.max
    """
    if month and year is None:
        raise ValueError("Cannot have a month without a year.")

    start, end = map(to_date, (start, end))
    if year is not None:
        if start or end:
            raise ValueError("Invalid arguments: cannot have a year with a start"
                             " or an end.")
        if isinstance(year, str):
            year = int(year)
        start = date(year, 1, 1)
        end = date(year, 12, 31)
        if month is not None:
            if isinstance(month, str):
                month = int(month)
            start = start.replace(month=month)
            end = (date(year + (month == 12), month % 12 + 1, 1)
                   - timedelta(days=1))
    if not start:
        start = date.min
    if not end:
        end = date.max
    return start, end


def timedelta_coefficient(start1, end1, start2, end2):
    timedelta1 = (end1 - start1 + timedelta(days=1)).days
    timedelta2 = (end2 - start2 + timedelta(days=1)).days
    return (float(timedelta2) / float(timedelta1))


def get_month_list(lang='fr'):
    if lang == 'fr':
        return ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    else:
        raise ValueError("Unknown langage : '%s'"%lang)


def get_month_name(num, lang='fr'):
    return get_month_list(lang=lang)[num-1]


def to_jstimestamp(mydatetime: str | datetime | date | None) -> float | None:
    mydatetime = to_date(mydatetime)
    if not mydatetime:
        return None

    timestamp_start = (datetime.combine(mydatetime, datetime.min.time())
                       - datetime(1970, 1, 1)) / timedelta(seconds=1)
    return int(timestamp_start) * 1e3  # Multiply by 1e3 as JS timestamp is in milliseconds

# MS = mois ; AS = an ; W = semaine ; D = jour
