#!/usr/bin/python
"""Run asynchronous tasks with gobject and coroutines."""
import gobject

def start_job(generator):
    """Start a job (a coroutine that yield tasks)."""
    def _task_return(result):
        def _advance_generator():
            try:
                new_task = generator.send(result)
            except StopIteration:
                return
            new_task(_task_return)
        # isolate the advance of the coroutine
        gobject.idle_add(_advance_generator)            
    _task_return(None)
    return generator

# Task examples

def sleep_task(secs):
    """Suspend job for the given number of seconds and return elapsed time."""
    def _task(task_return):
        start_time = time.time()
        def _on_timeout():
            task_return(time.time() - start_time)
        gobject.timeout_add(int(secs * 1000), _on_timeout)
    return _task

def threaded_task(function, *args, **kwargs):
    """Run function(*args, **kwargs) in a thread and return the value."""
    from Queue import Queue
    from threading import Thread
    def _task(task_return):
        def _thread(queue):
            queue.put(function(*args, **kwargs))
        def _manager(queue):
            if queue.empty():
                return True
            task_return(queue.get())
        queue = Queue()
        thread = Thread(target=_thread, args=(queue,))
        thread.setDaemon(True)
        thread.start()
        gobject.timeout_add(100, _manager, queue)
    return _task

###

import sys
import time
import random
import urllib2

def myjob(url):
    def download(url):
        return urllib2.urlopen(url).read()
    elapsed = yield sleep_task(random.uniform(0.0, 3.0))
    sys.stderr.write("[slept:%0.2f]" % elapsed)
    sys.stderr.write("[start:%s]" % url)
    html = yield threaded_task(download, url)
    sys.stderr.write("[HTML:%s:%d]" % (url, len(html)))

def basso_continuo():
    sys.stderr.write(".")
    return True

urls = ["http://www.google.com", "http://python.com", "http://www.pygtk.org"]
for url in urls:      
    sys.stderr.write("myjob: %s\n" % start_job(myjob(url)))    
gobject.timeout_add(100, basso_continuo)
gobject.threads_init()  # needed because we use threaded tasks
loop = gobject.MainLoop()
loop.run()
