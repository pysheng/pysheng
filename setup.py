#!/usr/bin/python
"""Download books from Google Books."""

from pysheng import VERSION
from distutils.core import setup
import platform

WIN32 = (platform.system() == 'Windows')

if WIN32:
    import py2exe

setup_kwargs = dict(
    name='pysheng',
    version=VERSION,
    description='Download books from Google Books',
    author='Arnau Sanchez',
    author_email='tokland@gmail.com',
    url='https://github.com/tokland/pysheng',
    packages=[
        'pysheng/'
    ],
    scripts=[
        'bin/pysheng',
        'bin/pysheng-gui'
        ],
    license='GNU Public License v3.0',
    long_description=' '.join(__doc__.strip().splitlines()),
    data_files=[
        ('share/pysheng',
            ('pysheng/main.glade',))
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP'
    ],
    options={
        'py2exe': {
            'packages': 'encodings',
            'includes': 'cairo, pango, pangocairo, atk, gobject'
        },
        'sdist': {
            'formats': 'zip'
        }
    }
)

if WIN32:
    setup_kwargs['windows'] = [
        {
            'script': 'bin/pysheng-gui',
            # 'icon_resources': [(1, 'a.ico')]
        }
    ]

setup(**setup_kwargs)
