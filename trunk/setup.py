#!/usr/bin/python
"""Download books from Google Books."""

from distutils.core import setup
#import py2exe

setup(
    name="pysheng",
    description="Download books from Google Books",
    author="Arnau Sanchez",
    author_email="tokland@gmail.com",
    url="http://code.google.com/p/Download books from Google Books",
    packages=[  
        "pysheng/",
    ],
    scripts=[
      "bin/pysheng",
      "bin/pysheng-gui",
	  ],
    license="GNU Public License v3.0",
    long_description=" ".join(__doc__.strip().splitlines()),
    data_files = [
        ('share/pysheng/',
            ('data/main.glade',)),
    ],
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ],
  options = {
    'py2exe' : {
      'packages': 'encodings',
      'includes': 'cairo, pango, pangocairo, atk, gobject',
    },
    'sdist': {
      'formats': 'zip',
    }
  },    
)
