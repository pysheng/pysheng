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

import unittest
import tempfile
import os

from pysheng import lib


class TestLibrary(unittest.TestCase):
    def create_temporal(self, data):
        fd, path = tempfile.mkstemp()
        os.write(fd, data)
        os.close(fd)
        return path

    # Tests

    def test_first(self):
        lst = [1, 2, 3, 4]
        self.assertEqual(lib.first(lst), 1)
        self.assertEqual(lib.first(iter(lst)), 1)
        self.assertEqual(None, lib.first([]))

    def test_download(self):
        data = """This is a test\n"""
        path = self.create_temporal(data)
        self.assertEqual(lib.download("file://%s" % path), data)

    def test_build_request(self):
        host = "exampleserver.org"
        url = "http://%s/1/2/file.html" % host
        postdata = {"var1": "value1", "var2": "value2"}
        request = lib.build_request(url, postdata)
        self.assertEqual(request.get_host(), host)
        self.assertEqual(request.get_method(), "POST")
        build = lambda d: "&".join("%s=%s" % pair for pair in d.iteritems())
        self.assertEqual(request.get_data(), build(postdata))


if __name__ == '__main__':
    unittest.main()
