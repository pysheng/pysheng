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
import sys
import time
import traceback
import functools
import string

import gtk
import gtk.glade
import gobject

from pysheng import lib
from pysheng import asyncjobs
import pysheng

HEADERS = {"User-Agent": pysheng.AGENT}

class State:
    def __init__(self):
        self.download_job = None
        self.check_job = None
        self.downloaded_images = None
        self.pdf_filename = None

def restart_buttons(widgets):
    set_sensitivity(widgets, check=True, start=True, pause=False, cancel=False)
    set_sensitivity(widgets, url=True, browse_destdir=True, page_start=True, page_end=True)
    widgets.progress_current.set_fraction(0.0)
    widgets.progress_current.set_text("")

def createfile(output_path, image_data):
    open(output_path, "wb").write(image_data)    

def set_sensitivity(widgets, **kwargs):
    for key, value in kwargs.iteritems():
        getattr(widgets, key).set_sensitive(value)    

def get_debug_func(widgets):
    buf = widgets.log.get_buffer()
    def _debug(line):
        stime = time.strftime("%H:%M:%S", time.localtime())
        buf.insert(buf.get_end_iter(), "[%s] %s\n" % (stime, line))
        widgets.log.scroll_to_iter(buf.get_end_iter(), 0)
    return _debug

def adj_int(value, adjvalue, default=None):
    if value is None:
        return default
    return value + adjvalue

def set_book_info(widgets, info):
    def italic(s):
        return "<i>%s</i>" % s
    if info:
        widgets.title.set_markup(italic(str(info["title"] or "-")))
        widgets.attribution.set_markup(italic(str(info["attribution"] or "-")))
        widgets.npages.set_markup(italic(str(len(info["page_ids"]))))
    else:
        widgets.title.set_markup(italic("-"))
        widgets.attribution.set_markup(italic("-"))
        widgets.npages.set_markup(italic("-"))
   
def string_to_valid_filename(s):   
    forbidden_chars = ":;'/\\?%*|\"<>"
    return "".join(c for c in s if c not in forbidden_chars)
        
def on_elapsed(widgets, name, elapsed, total):
    if total is not None:
        widgets.progress_current.set_fraction(float(elapsed)/total)
        name += " (%d bytes)" % total
    else:        
        widgets.progress_current.pulse()
    msg = "Downloading %s..." % name    
    widgets.progress_current.set_text("Downloading %s..." % name)

# Jobs

def get_info(widgets, url, opener):
    debug = widgets.debug
    html = yield asyncjobs.ProgressDownloadThreadedTask(
        url, opener, headers=HEADERS, 
        elapsed_cb=functools.partial(on_elapsed, widgets, "info"))
    try:
        info = pysheng.get_info(html)
    except ValueError, detail:
        debug("Error parsing page HTML: %s" % str(detail))
        raise
    debug("Info: attribution=%s" % info["attribution"]) 
    debug("Info: title=%s" % info["title"])
    debug("Info: total pages=%s" % len(info["page_ids"]))
    set_book_info(widgets, info)        
    raise StopIteration(info)

def download_book(widgets, state, url, page_start=0, page_end=None):
    """Yield (info, page, image_data) for pages from page_start to page_end"""
    try:
        set_sensitivity(widgets, start=False, pause=True, cancel=True,
            browse_destdir=False, page_start=False, page_end=False)
        destdir = widgets.destdir.get_text()
        debug = widgets.debug
        set_sensitivity(widgets, check=False, savepdf=False)
        debug("Output directory: %s" % destdir)
        debug("Page_start: %s, Page end: %s" % 
            (adj_int(page_start, +1, 1), adj_int(page_end, +1, "last")))
        opener = lib.get_cookies_opener()
        book_id = pysheng.get_id_from_string(url)
        debug("Book ID: %s" % book_id)
        cover_url = pysheng.get_cover_url(book_id)
        widgets.progress_all.set_fraction(0.0)
        widgets.progress_all.set_text('') 
        widgets.progress_current.set_pulse_step(0.04)
        state.downloaded_images = None
        info = yield get_info(widgets, cover_url, opener)
        if not widgets.page_start.get_text():
            widgets.page_start.set_text(str(1))
        if not widgets.page_end.get_text():
            widgets.page_end.set_text(str(len(info["page_ids"])))
        page_ids = info["page_ids"][page_start:adj_int(page_end, +1)]        
        namespace = dict(title=info["title"], attribution=info["attribution"])
        images = []
        for page, page_id in enumerate(page_ids):
            page += page_start
            if namespace["attribution"]:
                image_file_template = "%(attribution)s - %(title)s.page-%(page)03d"
            else:
                image_file_template = "%(title)s.page-%(page)03d"
            filename0 = (image_file_template+".png") % dict(namespace, page=page+1)
            filename = string_to_valid_filename(filename0.encode("utf-8"))
            output_path = os.path.join(destdir, filename)
            if os.path.exists(output_path):
                debug("Skip existing image: %s" % output_path)
                images.append(output_path)
                continue             
            relative_page = page - page_start + 1
            widgets.progress_all.set_fraction(float(relative_page-1)/len(page_ids))
            widgets.progress_all.set_text(
                "Total: %d%%" % (int(100*float(relative_page-1) / len(page_ids))))
            header = "[%d/%d] " % (relative_page, len(page_ids))
            debug(header + "Start page: %d (page_id: %s)" % (page+1, page_id))
            page_url = pysheng.get_page_url(info["prefix"], page_id)
            debug(header + "Download page contents: %s" % (page_url))
            widgets.progress_current.set_fraction(0.0)
            page_html = yield asyncjobs.ProgressDownloadThreadedTask(
                page_url, opener, headers=HEADERS,
                elapsed_cb=functools.partial(on_elapsed, widgets, "page"))
            
            image_url = pysheng.get_image_url_from_page(page_html)
            if not image_url:
              debug("No image for this page, probably access is restricted")
              continue            
            debug(header + "Download page image: %s" % image_url)
            widgets.progress_current.set_fraction(0.0)
            image_data = yield asyncjobs.ProgressDownloadThreadedTask(
                image_url, opener, headers=HEADERS,
                elapsed_cb=functools.partial(on_elapsed, widgets, "image"))            
            debug(header + "Image downloaded (%d bytes)" % len(image_data))
            createfile(output_path, image_data)            
            debug(header + "Image written: %s" % output_path)
            images.append(output_path)

        widgets.progress_all.set_fraction(1.0)
        widgets.progress_all.set_text("Done")                  
        debug("Done!")
        restart_buttons(widgets)
        state.downloaded_images = images
        if namespace["attribution"]:
            state.pdf_filename = "%(attribution)s - %(title)s.pdf" % namespace
        else:
            state.pdf_filename = "%(title)s.pdf" % namespace
        set_sensitivity(widgets, savepdf=True)        
    except asyncjobs.JobCancelled:
        return        
    except Exception, detail:
        traceback.print_exc()
        debug("job error: %s" % detail)
        restart_buttons(widgets)    

def check_book(widgets, url):    
    set_sensitivity(widgets, url=False, check=False, start=False, cancel=True)
    debug = widgets.debug
    debug("Checking book: %s" % url)
    try: 
        opener = lib.get_cookies_opener()
        book_id = pysheng.get_id_from_string(url)
        debug("Book ID: %s" % book_id)
        cover_url = pysheng.get_cover_url(book_id)
        set_book_info(widgets, None)
        info = yield get_info(widgets, cover_url, opener)
        widgets.page_start.set_text(str(1))
        widgets.page_end.set_text(str(len(info["page_ids"])))
        debug("Check book done")
        restart_buttons(widgets)
    except asyncjobs.JobCancelled:
        return
    except Exception, detail:
        traceback.print_exc()
        debug(Exception(detail))
        debug("Check book error")
        restart_buttons(widgets)

# Widget callbacks
     
def on_start__clicked(button, widgets, state):
    if state.download_job and state.download_job.is_alive():
        state.download_job.resume()
        set_sensitivity(widgets, pause=True, start=False)
        widgets.debug("Job resumed")
        return        
    url = widgets.url.get_text()
    page_start = (int(widgets.page_start.get_text())-1 if widgets.page_start.get_text() else 0)
    page_end = (int(widgets.page_end.get_text())-1 if widgets.page_end.get_text() else None)
    gen = download_book(widgets, state, url, page_start=page_start, page_end=page_end)
    state.download_job = asyncjobs.Job(gen)

def on_pause__clicked(button, widgets, state):
    state.download_job.pause()
    set_sensitivity(widgets, pause=False, start=True)
    widgets.debug("Job paused")

def on_check__clicked(button, widgets, state):
    url = widgets.url.get_text()
    state.check_job = asyncjobs.Job(check_book(widgets, url))

def on_url__changed(entry, widgets, state):
    value = bool(entry.get_text())
    set_sensitivity(widgets, start=value, check=value)

def on_url__activate(entry, widgets, state):
    if widgets.check.get_property("sensitive"):
        return on_check__clicked(None, widgets, state)

def on_page_start__activate(entry, widgets, state):
    if widgets.start.get_property("sensitive"):
        return on_start__clicked(None, widgets, state)

def on_page_end__activate(entry, widgets, state):
    if widgets.start.get_property("sensitive"):
        return on_start__clicked(None, widgets, state)

def clean_exit(widgets, state):
    if state.download_job and state.download_job.is_alive():  
        state.download_job.cancel()
    gtk.main_quit()
    
def on_exit__clicked(button, widgets, state):
    clean_exit(widgets, state)

def on_window__delete_event(window, event, widgets, state):
    clean_exit(widgets, state)
                
def on_cancel__clicked(button, widgets, state):
    if state.download_job and state.download_job.is_alive():    
        state.download_job.cancel() 
    if state.check_job and state.check_job.is_alive():    
        state.check_job.cancel()
    widgets.debug("Job cancelled")
    restart_buttons(widgets)

def on_browse_destdir__clicked(button, widgets, state):
    directory = os.path.expanduser(widgets.destdir.get_text())
    if not os.path.isdir(directory):
        directory = os.path.expanduser("~")
    chooser = gtk.FileChooserDialog(
        title="Select destination directory",
        action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
        buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
    chooser.set_current_folder(widgets.destdir.get_text())
    response = chooser.run()
    if response == gtk.RESPONSE_OK:
        directory = chooser.get_filename()
        widgets.destdir.set_text(directory)
    chooser.destroy()

def on_savepdf__clicked(button, widgets, state):    
    if not state.downloaded_images or not state.pdf_filename:
        widgets.debug("Error creating PDF")
        return
    try:
        from reportlab.lib import pagesizes
        from reportlab.lib.units import cm
    except ImportError:
        widgets.debug("You need to install ReportLab (http://www.reportlab.com/)" + 
            " to create a PDF")
        return
    chooser = gtk.FileChooserDialog(
        title="Save PDF",
        action=gtk.FILE_CHOOSER_ACTION_SAVE,
        buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
    chooser.set_current_folder(widgets.destdir.get_text())
    chooser.set_current_name(state.pdf_filename)
    chooser.set_do_overwrite_confirmation(True)
    response = chooser.run()
    if response == gtk.RESPONSE_OK:
        output_pdf = chooser.get_filename()
        try:
            lib.create_pdf_from_images(state.downloaded_images, output_pdf, 
                pagesize=pagesizes.A4, margin=0*cm)
            widgets.debug("PDF written: %s" % output_pdf)
        except Exception, exception:
            traceback.print_exc()
            debug("error creating PDF: %s" % exception)
    chooser.destroy()

###
                
def set_callbacks(namespace, widgets, state):
    callbacks_mapping = {
        "check": "clicked",
        "url": ["activate", "changed"],
        "page_start": "activate",
        "page_end": "activate",
        "start": "clicked",
        "exit": "clicked",
        "window": "delete-event",
        "cancel": "clicked",
        "pause": "clicked",
        "browse_destdir": "clicked",
        "savepdf": "clicked",
    }
    for widget_name, signals in callbacks_mapping.iteritems():
        if isinstance(signals, str):
            signals = [signals]
        for signal in signals:
            widget = getattr(widgets, widget_name)
            callback = namespace["on_%s__%s" % (widget_name, signal.replace("-", "_"))]
            widget.connect(signal, callback, widgets, state)
                
def view_init(widgets):
    set_sensitivity(widgets, start=False, check=False, pause=False, cancel=False)
    set_sensitivity(widgets, savepdf=False)
    widgets.page_start.set_text("1")
    #widgets.destdir.set_text(os.path.expanduser("~"))
    widgets.destdir.set_text(os.getcwd())

def load_glade(filename, root, widget_names):
    wtree = gtk.glade.XML(filename, root)
    dwidgets = {}
    for name in widget_names:
        widget = wtree.get_widget(name)
        if not widget:
            raise ValueError, "Widget name not found: %s" % name
        dwidgets[name] = widget
    return lib.Struct(**dwidgets)

def run(book_url=None):
    widget_names = [
        "window", "url", "destdir", "check", "start", "cancel", 
        "pause", "exit", "log", "page_start", "page_end", 
        "title", "attribution", "npages", "browse_destdir", 
        "progress_all", "progress_current", "savepdf",
    ]
    for filepath in ["data/main.glade", "/usr/share/pysheng/main.glade"]:
        if os.path.isfile(filepath):
            break
    else:
        raise ValueError, "cannot find glade file: main.glade"
    widgets = load_glade(filepath, "window", widget_names)    
    state = State()
    widgets.debug = get_debug_func(widgets)
    widgets.window.set_title("PySheng v%s: Google Books downloader" % pysheng.VERSION)
    view_init(widgets)
    set_callbacks(globals(), widgets, state)
    if book_url:
        widgets.url.set_text(book_url)
    return widgets, state

def main(args):
    widgets, state = run()
    widgets.window.show_all()
    gtk.main()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
