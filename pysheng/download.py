#!/usr/bin/python

# Copyright (c) Arnau Sanchez <tokland@gmail.com>

# This script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>

import os
import re
import sys
import itertools
import HTMLParser

try:
    # Python >= 2.6
    import json
except ImportError:
    import simplejson as json

import lib

AGENT = "Chrome 5.0"


class ParsingError(Exception):
    pass


def get_id_from_string(s):
    """Return book ID from a string (can be a book code or URL)."""
    if "/" not in s:
        return s
    url = s
    match = re.search("[?&]?id=([^&]+)", url)
    if not match:
        raise ParsingError('Error extracting id query string from URL: %s' %
                           url)
    return match.group(1)


def get_cover_url(book_id):
    url = "http://books.google.com/books"
    return "%s?id=%s&hl=en&printsec=frontcover&source=gbs_ge_summary_r&cad=0" \
           % (url, book_id)


def get_unescape_entities(s):
    parser = HTMLParser.HTMLParser()
    return parser.unescape(s)


def get_info(cover_html):
    """Return dictionary with the book information.

    Include the prefix, page_ids, title and attribution."""
    tag = lib.first(s for s in cover_html.split("<")
                    if re.search('input[^>]*\s+name="?ie"?', s))
    if tag:
        match = re.search('value="(.*?)"', tag)
        if not match:
            raise ParsingError('Cannot find encoding info')
        encoding = match.group(1).lower()
    else:
        encoding = "iso8859-15"
    match = re.search(r'_OC_Run\((.*?)\);', cover_html)
    if not match:
        raise ParsingError('No JS function OC_Run() found in HTML')
    oc_run_args = json.loads("[%s]" % match.group(1), encoding=encoding)
    if len(oc_run_args) < 2:
        raise ParsingError('Expecting at least 2 arguments in function: '
                           'OC_Run()')
    pages_info, book_info = oc_run_args[:2]
    if "page" not in pages_info:
        raise ParsingError('Cannot find page info')
    page_ids = [x["pid"] for x in sorted(pages_info["page"],
                                         key=lambda d: d["order"])]
    if not page_ids:
        raise ParsingError('No page_ids found')
    prefix = pages_info["prefix"].decode("raw_unicode_escape")
    mw = book_info["max_resolution_image_width"]
    mh = book_info["max_resolution_image_height"]
    return {
        "prefix": prefix,
        "page_ids": page_ids,
        "title": get_unescape_entities(book_info["title"]),
        "attribution": get_unescape_entities(re.sub("^By\s+", "",
                                                    book_info["attribution"])),
        "max_resolution": (mw, mh),
    }


def get_image_url_from_page(html):
    """Get image from a page html."""
    if "/googlebooks/restricted_logo.gif" in html:
        return
    else:
        match = re.search(r"preloadImg.src = '([^']*?)'", html)
        if not match:
            raise ParsingError('No image found in HTML page')
        else:
            return match.group(1).decode("string-escape")


def get_page_url(prefix, page_id):
    return prefix + "&pg=" + page_id


def download(*args, **kwargs):
    return lib.download(*args, **dict(kwargs, agent=AGENT))


def get_info_from_url(url):
    opener = lib.get_cookies_opener()
    cover_url = get_cover_url(get_id_from_string(url))
    cover_html = download(cover_url, opener=opener)
    return get_info(cover_html)


def download_book(url, page_start=0, page_end=None):
    """Yield tuples (info, page, image_data) for each page of the book
       <url> from <page_start> to <page_end>"""
    info = get_info_from_url(url)
    opener = lib.get_cookies_opener()
    page_ids = itertools.islice(info["page_ids"], page_start, page_end)

    for page0, page_id in enumerate(page_ids):
        page = page0 + page_start
        page_url = get_page_url(info["prefix"], page_id)
        page_html = download(page_url, opener=opener)
        image_url0 = get_image_url_from_page(page_html)
        if image_url0:
            width, height = info["max_resolution"]
            image_url = re.sub("w=(\d+)", "w=" + str(width), image_url0)
            image_data = download(image_url, opener=opener)
            yield info, page, image_data


def main(args):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--page-start', dest='page_start', type=int,
                        default=1, help='Start page')
    parser.add_argument('-e', '--page-end', dest='page_end', type=int,
                        default=None, help='End page')
    parser.add_argument('-n', '--no-redownload', dest='noredownload',
                        action="store_true", default=False,
                        help='Do not re-download pages if they exist locally')
    parser.add_argument('-q', '--quiet', dest='quiet',
                        action="store_true", default=False,
                        help='Do not print messages to the terminal')
    parser.add_argument('url', help='GOOGLE_BOOK_OR_ID')
    args = parser.parse_args(args)

    url = args.url
    info = get_info_from_url(url)
    namespace = dict(title=info["title"], attribution=info["attribution"])
    output_directory = "%(attribution)s - %(title)s" % namespace
    lib.mkdir_p(output_directory)

    for page_info, page, image_data in\
            download_book(url, args.page_start - 1, args.page_end):
        filename = "%03d.png" % (page + 1)
        output_path = os.path.join(output_directory, filename)
        if not ((os.path.isfile(output_path) and
                 args.noredownload)):
            open(output_path, "wb").write(image_data)
            if not args.quiet:
                print 'Downloaded {}'.format(output_path)
        elif not args.quiet:
            print 'Output file {} exists'.format(output_path)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
