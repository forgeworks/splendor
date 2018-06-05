import datetime
import timeit
import re
import arrow
import udatetime
import rfc3339
import strict_rfc3339
from dateutil.parser import parse

first = "1980-06-16T10:15:23-04:00"
second = "2018-05-05T01:30:00Z"

def test_dateutil():
    return (
        parse(first),
        parse(second)
    )


reg = re.compile(r'^(?P<fullyear>\d{4})-(?P<month>0[1-9]|1[0-2])-(?P<mday>0[1-9]|[12][0-9]|3[01])T(?P<hour>[01][0-9]|2[0-3]):(?P<minute>[0-5][0-9]):(?P<second>[0-5][0-9]|60)(?P<secfrac>\.[0-9]+)?(Z|(\+|-)(?P<offset_hour>[01][0-9]|2[0-3]):(?P<offset_minute>[0-5][0-9]))$')
def parse_regex_datetime(dt):
    year, month, day, hour, minute, seconds, microsec, offset, _, offset_hour, offset_minute = reg.match(first).groups()
    tz = datetime.timezone(datetime.timedelta(hours=int(offset_hour), minutes=int(offset_minute)))
    if microsec is not None:
        return datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(seconds), int(microsec), tzinfo=tz)
    else:
        return datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(seconds), tzinfo=tz)


def test_regex():
    return (
        parse_regex_datetime(first),
        parse_regex_datetime(second)
    )


def test_arrow():
    return (
        arrow.get(first),
        arrow.get(second),
    )


def test_udatetime():
    return (
        udatetime.from_string(first),
        udatetime.from_string(second),
    )


def test_rfc3339():
    return (
        rfc3339.parse_datetime(first),
        rfc3339.parse_datetime(second)
    )


def test_strict_rfc3339():
    return (
        strict_rfc3339.rfc3339_to_timestamp(first),
        strict_rfc3339.rfc3339_to_timestamp(second)
    )


print("DateUtil:")
print( "", test_dateutil())
print( "", timeit.timeit(test_dateutil, number=10000) )

print("Arrow:")
print( "", test_arrow())
print( "", timeit.timeit(test_arrow, number=10000) )

print("Regex:")
print( "", test_regex())
print( "", timeit.timeit(test_regex, number=10000) )

print("rfc3339:")
print( "", test_rfc3339())
print( "", timeit.timeit(test_rfc3339, number=10000) )

print("strict-rfc3339:")
print( "", test_strict_rfc3339())
print( "", timeit.timeit(test_strict_rfc3339, number=10000) )

print("UDateTime:")
print( "", test_udatetime())
print( "", timeit.timeit(test_udatetime, number=10000) )


