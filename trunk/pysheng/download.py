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

import re
import sys
import itertools

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
        raise ParsingError, "Error extracting id query string from URL: %s" % url
    return match.group(1)

def get_cover_url(book_id):
    return "http://books.google.com/books?id=%s&hl=en&printsec=frontcover" % book_id
    
def get_info(cover_html):
    """Return dictionary with the book info (prefix, page_ids, title, attribution)."""
    tag = lib.first(s for s in cover_html.split("<") 
        if re.search('input[^>]*\s+name="?ie"?', s))
    if tag:
        match = re.search('value="(.*?)"', tag)
        if not match:
            raise ParsingError, "Cannot found encoding info"
        encoding = match.group(1).lower()
    else:
        encoding = "iso8859-15"
    match = re.search(r'_OC_Run\((.*?)\);', cover_html)
    if not match:
        raise ParsingError, "No JS function OC_Run() found in HTML"
    oc_run_args = json.loads("[%s]" % match.group(1), encoding=encoding)
    if len(oc_run_args) < 2:
        raise ParsingError, "Expecting at least 2 arguments in function OC_Run()"
    pages_info, book_info = oc_run_args[:2]
    page_ids = [x["pid"] for x in sorted(pages_info["page"], key=lambda d: d["order"])]
    if not page_ids:
        raise ParsingError, "No page_ids found"
    prefix = pages_info["prefix"].decode("raw_unicode_escape")
    return {
        "prefix": prefix, 
        "page_ids": page_ids,
        "title": book_info["title"],
        "attribution": re.sub("^By\s+", "", book_info["attribution"]),
    }

def get_image_url_from_page(html):
    """Get image from a page html."""
    if "/googlebooks/restricted_logo.gif" in html:
        return 
    match = re.search(r"preloadImg.src = '([^']*?)'", html)
    if not match:
        raise ParsingError, "No image found in HTML page"
    return match.group(1)

def get_page_url(prefix, page_id):
    return prefix + "&pg=" + page_id

def download(*args, **kwargs):
    return lib.download(*args, **dict(kwargs, agent=AGENT))

def download_book(url, page_start=0, page_end=None):
    """Yield (info, page, image_data) for pages from page_start to page_end"""
    opener = lib.get_cookies_opener()
    cover_url = get_cover_url(get_id_from_string(url))
    cover_html = download(cover_url, opener=opener)
    info = get_info(cover_html)
    page_ids = itertools.islice(info["page_ids"], page_start, page_end)
    for page, page_id in enumerate(page_ids):
        page += page_start
        page_url = get_page_url(info["prefix"], page_id)
        page_html = download(page_url, opener=opener)
        image_url = get_image_url_from_page(page_html)
        if image_url:
          image_data = download(image_url, opener=opener)
          yield info, page, image_data
        
def main(args):
    import optparse
    usage = """usage: %prog GOOGLE_BOOK_OR_ID

    Download a Google Book and create a PNG image for each page.""" 
    parser = optparse.OptionParser(usage)
    options, args0 = parser.parse_args(args)
    if not args:
        parser.print_usage()
        return 2    
    url, = args
    image_file_template = "%(attribution)s - %(title)s.page-%(page)03d"
    for info, page, image_data in download_book(url):
        namespace = dict(title=info["title"], attribution=info["attribution"])
        output_file = ((image_file_template+".png") % 
          dict(namespace, page=page+1)).encode("utf-8")
        open(output_file, "wb").write(image_data)
        print output_file

  
if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
