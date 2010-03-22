#!/usr/bin/python

# Copyright (c) 2008-2009 Arnau Sanchez <tokland@gmail.com>

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

import cookielib
import itertools
import urllib2
import urllib
import sys
import re
import os

class Struct:
    """Struct/record-like class"""
    def __init__(self, **entries):
        self.__dict__.update(entries)

    def __repr__(self):
        args = ('%s=%s' % (k, repr(v)) for (k,v) in vars(self).iteritems())
        return 'Struct(%s)' % (', '.join(args))

def tostr(obj, default_encoding="utf-8"):
    """Convert object to string."""
    return (obj.encode(default_encoding) if isinstance(obj, unicode) else str(obj))

def debug(obj):
    """Write obj to standard error"""
    sys.stderr.write("--- " + tostr(obj) + "\n")
    sys.stderr.flush()
   
def first(iterable, pred=bool):
    """Return first item in iterator that matches the predicate."""
    for item in iterable:
        if pred(item):
            return item
                                          
def download(url, opener=None, agent='Mozilla/5.0 (X11; U; Linux x86_64)'):
    """Download a URL, optionally using a urlib2.opener"""
    opener = opener or urllib2.build_opener() 
    request = (url if isinstance(url, urllib2.Request) else build_request(url))
    if agent:
        request.add_header('User-Agent', agent)
    return opener.open(request).read()

def build_request(url, postdata=None):
    """Build a URL request with (optional) POST data"""
    data = (urllib.urlencode(postdata) if postdata else None)
    return urllib2.Request(url, data)

def get_cookies_opener(filename=None):
    """Open a cookies file and return a urllib2 opener object"""
    cookie_jar = cookielib.FileCookieJar()
    if filename:
        cookie_jar.load(filename)    
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))
    opener.cookie_jar = cookie_jar
    return opener
  
def create_pdf_from_images(image_paths, output_pdf, pagesize=None, margin=None):
    """Create a pdf from a sequence of images (one page per image)."""
    from reportlab.pdfgen import canvas
    from reportlab.lib import pagesizes
    from reportlab.lib.units import cm, mm, inch, pica
    pagesize = pagesize or pagesizes.A4
    margin = margin or 0*cm
        
    page_width, page_height = pagesize
    width = page_width - 2 * margin
    height = page_height - 2 * margin
    c = canvas.Canvas(output_pdf, pagesize=pagesize)
    for image_path in image_paths:
        c.drawImage(image_path, margin, margin, width, height)
        c.showPage()
    c.save()
