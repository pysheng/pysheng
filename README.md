Download books from Google Books as PNG images. It can be run either from the command-line or using a simple GUI (graphical interface). It should work out-of-the box for Unix systems (GNU/Linux, BSD) and (hopefully) for Windows.

Install
=======

For UNIX systems:

```
$ wget http://pysheng.googlecode.com/files/pysheng-VERSION.tgz
$ tar xvzf pysheng-VERSION.tgz
$ cd pysheng-VERSION
```

To install locally:

```
$ python setup.py install --user
```

To install system-wide:

```
$ sudo python setup.py install
```

Usage
=====

Using the GUI
=============

Note that in order to save a PDF you need [ReportLab](http://www.reportlab.com/software/opensource/) installed.

```
$ pysheng-gui
```

http://pysheng.googlecode.com/svn/wiki/screenshot1.png

Command line
============

 * Download a whole book:

```
$ pysheng "http://books.google.com/books?id=m5w5PRj5Nj4C"
```

 * Download a whole book using the command-line and convert the images into a single PDF (requires [Imagemagick](http://www.imagemagick.org/script/index.php)). Notice that you can use the Book ID only.

```
$ convert $(pysheng "m5w5PRj5Nj4C") book.pdf
```
