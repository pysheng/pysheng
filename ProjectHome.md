**PySheng** downloads a book from Google Books and saves a PNG image for each page or a single PDF. It can be run either from the command-line or using a simple GUI (graphical interface). It should work out-of-the box for Unix systems (GNU/Linux, BSD) and (hopefully) for Windows.

## Install ##

For UNIX systems:

```
$ wget http://pysheng.googlecode.com/files/pysheng-VERSION.tgz
$ tar xvzf pysheng-VERSION.tgz
$ cd pysheng-VERSION
$ sudo python setup.py install
```

## Usage ##

### GUI ###

Note that in order to save a PDF you need [ReportLab](http://www.reportlab.com/software/opensource/) installed.

```
$ pysheng-gui
```

![http://pysheng.googlecode.com/svn/wiki/screenshot1.png](http://pysheng.googlecode.com/svn/wiki/screenshot1.png)

### Command line ###

  * Download a whole book:

```
$ pysheng "http://books.google.com/books?id=m5w5PRj5Nj4C"
```

  * Download a whole book using the command-line and convert the images into a single PDF (requires [Imagemagick](http://www.imagemagick.org/script/index.php)). Notice that you can use the Book ID only.

```
$ convert $(pysheng "m5w5PRj5Nj4C") book.pdf
```



---

_Note: If you are both an experienced Python programmer and a Windows user you can help other users packaging pysheng. Contact me for further details._