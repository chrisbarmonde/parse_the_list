"""
Copyright (C) 2011 by Chris Barmonde (http://chris.barmon.de)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import re
import json

def get_show():
    """Return a skeleton object for a show"""
    return {
        'dates': [],
        'dow': '',
        'bands': [],
        'venue': '',
        'metadata': {
            'age': 0,
            'cost': 0,
            'time': '',
            'recommended': 0,
            'will_sell_out': False,
            'under_21_pays_more': False,
            'pit_warning': False,
            'no_ins_outs': False,
            'other': []
        }
    }

# Checks for the minimum age of a show. Can be a/a or some combination of numbers and such
age_regex = re.compile('^(a\/a|\d+[+])$', re.I)

# Checks for the time a show starts
time_regex = re.compile('^([\/\s]?\d+(\:\d{2})?[ap]m)+$', re.I)

months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']


def find_date(show, parts, month=''):
    """
    Determines which dates the show starts on. This can happen in a number of different formats that I've encountered:

    jul 15 fri
    jul 15/16
    jul 15/16/17
    jul 15-17
    jul 31/aug 1
    jul 31/aug 1/2
    jul 31 aug 1/2/3

    Could probably change at any damn time.
    """

    while len(parts) > 0:
        part = parts.pop()
        if part in months:
            month = part
        elif part.isdigit():
            show['dates'].append((month, part))
        elif '/' in part:
            new_parts = part.split('/')
            new_parts.reverse()
            find_date(show, new_parts, month)
        elif '-' in part:
            new_parts = part.split('-')

            # Check here to make sure we actually have a date range and not some crazy band name???
            if len(new_parts) != 2 or not new_parts[0].isdigit() or not new_parts[1].isdigit():
                parts.append(part)
                break

            for day in range(int(new_parts[0]), int(new_parts[1])+1):
                show['dates'].append((month, day))
        elif part in days:
            show['dow'] = part
            break
        else:
            parts.append(part)
            break



def find_bands(show, parts):
    """
    Finds all the bands for a given show. Bands can span across multiple lines, apparently depending on
    whether or not there's a comma at the end of the line. Beyond that, bands can have some kind of 'metadata'
    attached, like where they come from or if it's a special show like a CD release or some such.
    """
    has_more_bands = True
    has_venue = False

    find_match = False

    band = []
    while len(parts) > 0:
        part = parts.pop()
        if part == "at":
            has_venue = True
            has_more_bands = False
            break
        elif part[0] == '(' and not (part[-2] == ')' or part[-1] == ')'):
            find_match = True
        elif part[-1] == ',' and (not find_match or part[-2] == ')'):
            band.append(part[0:-1])
            show['bands'].append(' '.join(band))
            band[:] = []
            find_match = False
            continue

        band.append(part)

    if band:
        show['bands'].append(' '.join(band))

    return has_more_bands, has_venue

def find_venue(show, parts):
    """
    Finds the venue for the show. Venues are a little tricky because they can be just cities, full addresses,
    just venue names, and any other kind of combination. You essentially just have to search from the end of the
    last band up to where the age group is specified and hope for the best.
    """
    venue = []
    while len(parts) > 0:
        part = parts.pop()
        # If we've found the age, we're found the end of the venue.
        if age_regex.match(part):
            parts.append(part)
            show['venue'] = ' '.join(venue)
            break

        venue.append(part)

def find_metadata(show, parts):
    """
    Searches for all the different metadata for a show. This includes:

    a/a or \d+ :  Age limit of the show
    ##:##(a|p)m: Along with some other variations for the time of the show
    $##(\.##)? : How much the show costs
    *+         : How recommended the show is (more stars is more betterer)
    ^          : Under 21 must pay more for the show (wtf, who does this?)
    @          : Pit warning. My kinda show. Get out of my way, sucka.
    #          : No ins/outs. Once you're in, you're there for life. Kinda like a gang, I guess.
    $          : The show will likely sell out in advance.
    """
    find_match = False
    other = []

    while len(parts) > 0:
        part = parts.pop()

        if find_match:
            other.append(part)
            if part[-1] == ')':
                show['metadata']['other'].append(' '.join(other))
                find_match = False
                other[:] = []
            continue

        if part[0] == '*':
            show['metadata']['recommended'] = len(part)
        elif part[0] == '@':
            show['metadata']['pit_warning'] = True
        elif part[0] == '#':
            show['metadata']['no_ins_outs'] = True
        elif part[0] == '^':
            show['metadata']['under_21_pays_more'] = True
        elif part[0] == '$':
            if len(part) == 0:
                show['metadata']['will_sell_out'] = True
            else:
                show['metadata']['cost'] = part[1:]
        elif age_regex.match(part):
            show['metadata']['age'] = part
        elif time_regex.match(part):
            show['metadata']['time'] = part
        elif part == 'free':
            show['metadata']['cost'] = 0
        elif part[0] == '(':
            find_match = True
            other.append(part)
        else:
            show['metadata']['other'].append(part)



if __name__ == '__main__':
    show = {}
    shows = []
    with open('list-example.txt', 'r') as f:
        has_more_bands = False
        has_venue = False
        found_venue = False

        for line in f:
            parts = line.split()
            parts.reverse()

            if not line[0].isspace():
                has_venue = False
                found_venue = False

                if show:
                    shows.append(show)

                show = get_show()

                find_date(show, parts)
                has_more_bands = True


            if has_more_bands:
                has_more_bands, has_venue = find_bands(show, parts)
                if has_more_bands:
                    continue

            if has_venue:
                find_venue(show, parts)
                found_venue = True

            if found_venue:
                find_metadata(show, parts)


    if show:
        shows.append(show)

    w = open('list.json', 'w')
    w.write(json.dumps(shows))
    print('Done\n')
