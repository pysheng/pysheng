#!/usr/bin/python
import unittest
import gtk
import time
import os

import pysheng
from pysheng import gui

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
HTML_DIR = os.path.join(TESTS_DIR, "html")


def refresh_gui(delay=0.0):
    while gtk.events_pending():
        gtk.main_iteration_do(block=False)
    time.sleep(delay)


class PyshengGUITest(unittest.TestCase):
    def setUp(self):
        self.widgets, self.state = gui.run()
        get_info_original = pysheng.get_info

        def get_info_stub(html):
            info = get_info_original(html)
            info["page_ids"] = info["page_ids"][:3]
            return info
        pysheng.get_info = get_info_stub

        def get_cover_url_stub(book_id):
            return "file://" + os.path.join(HTML_DIR, "cover.html")

        def get_page_url_stub(prefix, page_id):
            return "file://" + os.path.join(HTML_DIR, "page.html")

        def get_image_url_from_page_stub(page_html):
            return "file://" + os.path.join(HTML_DIR, "image.png")
        pysheng.get_cover_url = get_cover_url_stub
        pysheng.get_page_url = get_page_url_stub
        pysheng.get_image_url_from_page = get_image_url_from_page_stub

        def createfile_stub(path, data):
            pass
        gui.createfile = createfile_stub

    def complete_job(self, name0):
        name = name0 + "_job"
        while not getattr(self.state, name):
            refresh_gui(0.1)
        while getattr(self.state, name).is_alive():
            refresh_gui(0.1)

    def assertSensitive(self, *widget_names):
        for name in widget_names:
            sensitive = getattr(self.widgets, name).get_property("sensitive")
            self.assertTrue(sensitive)

    def assertNotSensitive(self, *widget_names):
        for name in widget_names:
            sensitive = getattr(self.widgets, name).get_property("sensitive")
            self.assertFalse(sensitive)

    def test_init(self):
        self.assertNotSensitive("check", "start")
        self.assertNotSensitive("pause", "cancel")
        self.assertFalse(self.widgets.url.get_text())

    def test_check_process(self):
        self.assertNotSensitive("check")
        self.widgets.url.set_text("abookid")
        refresh_gui()
        self.assertSensitive("check")
        self.widgets.check.clicked()
        refresh_gui()
        self.assertEqual("-", self.widgets.title.get_text())
        self.assertEqual("-", self.widgets.attribution.get_text())
        self.assertEqual("-", self.widgets.npages.get_text())
        self.assertNotSensitive("check", "start", "pause")
        self.assertSensitive("cancel")
        self.complete_job("check")
        self.assertEqual("Artistic Theory in Italy",
                         self.widgets.title.get_text())
        self.assertEqual("Anthony Blunt", self.widgets.attribution.get_text())
        self.assertEqual("3", self.widgets.npages.get_text())
        self.assertSensitive("url", "check", "start")

    def test_check_cancel_process(self):
        self.widgets.url.set_text("abookid")
        refresh_gui()
        self.widgets.check.clicked()
        refresh_gui()
        self.assertSensitive("cancel")
        self.widgets.cancel.clicked()
        self.complete_job("check")
        self.assertSensitive("url", "check", "start")

    def test_start_process(self):
        self.assertNotSensitive("start")
        self.widgets.url.set_text("abookid")
        refresh_gui()
        self.assertSensitive("start")
        self.widgets.start.clicked()
        refresh_gui()
        self.assertNotSensitive("check", "start", "browse_destdir",
                                "page_start", "page_end")
        self.assertSensitive("cancel")
        self.complete_job("download")
        self.assertSensitive("url", "check", "start", "browse_destdir",
                             "page_start", "page_end")

    def test_start_cancel_process(self):
        self.widgets.url.set_text("abookid")
        refresh_gui()
        self.widgets.start.clicked()
        refresh_gui()
        self.assertSensitive("cancel")
        self.widgets.cancel.clicked()
        refresh_gui()
        self.complete_job("download")
        self.assertSensitive("url", "check", "start")

    def test_start_pause_and_continue(self):
        self.widgets.url.set_text("abookid")
        refresh_gui()
        self.widgets.start.clicked()
        refresh_gui()
        self.assertSensitive("pause")
        self.widgets.pause.clicked()
        refresh_gui()
        self.assertSensitive("start")
        self.widgets.start.clicked()
        self.complete_job("download")


if __name__ == '__main__':
    unittest.main()
