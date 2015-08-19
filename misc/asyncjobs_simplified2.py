import time
import functools
from threading import Thread
from Queue import Queue
import types

import gobject

class Job:
    """Wrap a co-routines that yields asynchronous tasks (see Task class)."""
    def __init__(self, generator):
        self.generators = [generator]
        self._advance_task(generator, "send", None)

    def _start_task(self, task, generator):
        return_cb = functools.partial(self._advance_task, generator, "send")
        exception_cb = functools.partial(self._advance_task, generator, "throw")
        task.config(return_cb, exception_cb)
        task.run()

    def _advance_task(self, generator, method, result=None):
        while 1:
            try:
                task_generator_or_result = getattr(generator, method)(result)
            except StopIteration:
                self.generators.remove(generator)
                generator.close()
                if not self.generators:
                    return
                generator = self.generators[-1]
                method, result = "send", None
                continue
            if isinstance(task_generator_or_result, types.GeneratorType):
                generator = task_generator_or_result
                self.generators.append(generator)
                method, result = "send", None
                continue
            elif isinstance(task_generator_or_result, Task):
                task = task_generator_or_result
                self._start_task(task, generator)
                return
            else:
                self.generators.remove(generator)
                generator.close()
                if not self.generators:
                    raise RuntimeError, "Unexpected state: job has no generators"
                generator = self.generators[-1]
                method, result = "send", task_generator_or_result


class TaskError(Exception):
    pass

class Task:
    """Base class for asynchronous tasks."""
    def config(self, return_cb, exception_cb):
        """Set return and exception callbacks."""
        self.return_cb = return_cb
        self.exception_cb = exception_cb

    def run(self):
        raise RuntimeError, "Run method must be overriden"

# Tasks examples

class SleepTask(Task):
    """Sleep for some time and return."""
    def __init__(self, seconds):
        self.seconds = seconds

    def run(self):
        def _return():
            self.return_cb(self.seconds)
            return False
        self.source_id = gobject.timeout_add(int(self.seconds * 1000), _return)

class ThreadedTask(Task):
    """Run a function in a new thread and return its output."""
    def __init__(self, fun, *args, **kwargs):
        self.function = (fun, args, kwargs)

    def run(self):
        """Start thread and set callback to get the result value."""
        queue = Queue()
        thread = Thread(target=self._thread, args=(self.function, queue))
        thread.setDaemon(True)
        thread.start()
        self.source_id = gobject.timeout_add(50, self._queue_manager, thread, queue)

    def _queue_manager(self, thread, queue):
        if queue.empty():
            if not thread.isAlive():
                # Thread is not active and the queue is empty: something went wrong!
                self.exception_cb(TaskError)
                return False
            return True
        rtype, rvalue = queue.get()
        if rtype == "return":
            self.return_cb(rvalue)
        else:
            self.exception_cb(rvalue)
        return False

    def _thread(self, function, queue):
        fun, args, kwargs = function
        try:
            result = fun(*args, **kwargs)
        except Exception, exception:
            queue.put(("exception", exception))
            raise
        queue.put(("return", result))

# Usage example with PyGTK

def heavy_function(x, y):
    time.sleep(1.0)
    return int(x) + int(y)

def nested_job(wait):
    sys.stderr.write("[NJW1%0.1f]" % wait)
    yield SleepTask(wait/2.0)
    sys.stderr.write("[NJW2%0.1f]" % wait)
    yield SleepTask(wait/2.0)
    yield "hello"

def my_job(wait, a, b):
    sys.stderr.write("[H1,%s,%s]" % (a, b))
    result1 = (yield ThreadedTask(heavy_function, a, b))
    sys.stderr.write("[H2,%s,%s]" % (result1, b))
    result = (yield nested_job(wait))
    assert result == "hello"
    result2 = (yield ThreadedTask(heavy_function, result1, b))
    sys.stderr.write("[RES:%s]" % result2)

def other_async_work():
    import sys
    sys.stderr.write(".")
    return True

def on_start(button, entrya, entryb):
    import random
    job = Job(my_job(random.uniform(1, 5), entrya.get_text(), entryb.get_text()))
    sys.stderr.write("J%d" % id(job))

def main(args):
    import gtk
    gobject.threads_init()
    window = gtk.Window()
    start = gtk.Button("start")
    window.connect("delete-event", lambda *args: gtk.main_quit())
    box = gtk.VBox()
    entrya, entryb = gtk.Entry(), gtk.Entry()
    entrya.set_text("1")
    entryb.set_text("2")
    start.connect("clicked", on_start, entrya, entryb)
    for widget in (entrya, entryb, start):
        box.pack_start(widget)
    window.add(box)
    start.set_flags(gtk.CAN_DEFAULT)
    entrya.set_activates_default(True)
    entryb.set_activates_default(True)
    window.set_default(start)
    window.show_all()

    gobject.timeout_add(100, other_async_work)
    gtk.main()

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
