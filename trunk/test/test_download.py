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

import unittest
import StringIO
import sys
import os

import pysheng

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
HTML_DIR = os.path.join(TESTS_DIR, "html")

class TestLibrary(unittest.TestCase):        
    def setUp(self):
        pass
    
    def test_get_id_from_url(self):
        get = pysheng.get_id_from_string
        self.assertEqual("2TowtKyI27wC", 
          get("2TowtKyI27wC"))
        self.assertEqual("2TowtKyI27wC", 
          get("http://books.google.com/books?id=2TowtKyI27wC&printsec=frontcover"))
        self.assertEqual("2TowtKyI27wC", 
          get("http://books.google.com/books?key=value&id=2TowtKyI27wC"))
          
    def test_get_info(self):
        htmlcover = open(os.path.join(HTML_DIR, "cover.html")).read()
        info = pysheng.get_info(htmlcover)
        self.assertEqual('http://books.google.com/books?id=2TowtKyI27wC&lpg=PP1&ie=ISO-8859-1', info["prefix"])
        self.assertEqual(172, len(info["page_ids"]))
        self.assertEqual("Artistic Theory in Italy", info["title"])
        self.assertEqual("Anthony Blunt", info["attribution"])
        
    def test_get_image_url_from_page(self):
        htmlpage = open(os.path.join(HTML_DIR, "page.html")).read()
        image_url = pysheng.get_image_url_from_page(htmlpage)
        self.assertEqual("http://books.google.es/books?id=2TowtKyI27wC&pg=PP1&"+
            "img=1&zoom=3&hl=es&sig=ACfU3U03m8rmh6AXb1HJuIRL_FF7cMQbiw"+
            "&w=685", image_url)        
    
if __name__ == '__main__':
    unittest.main()
