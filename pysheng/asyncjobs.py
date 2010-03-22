#!/usr/bin/python
"""
Asynchronous jobs using co-routines and gobject.

The use of gobject is hardcoded, but it should be easy to change it
with any other events-based loop library.

The goal of this module is to allow a programmer to write PyGTK apps without 
resorting to complicated callbacks on blocking functions. The use of 
threads for some operations (downloading) is required so as to use 
high-level urllib2 functions, but they are avoided whenever possible
(a non-blocking urllib2 is feasible using libraries as eventlet or gevent,
take a look on them if using threads is a no-no for you).
"""
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

import time
from threading import Thread, Event
from Queue import Queue, Empty
import StringIO
import urllib2
import functools
import types

import gobject
gobject.threads_init()

JobCancelled = GeneratorExit

class TaskError(Exception):
    """Something wrong was detected in a task and it must be aborted."""
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return str(self.reason)

class Job:
    """
    An asynchronous job must be instantiated with a generator/co-routine that
    yield asynchronous tasks.
    
    States: running (default on start), cancel, paused, cancelled, finished.    
    """ 
    def __init__(self, generator):
        self.generators = [generator]
        self._paused_task = None
        self.current_task = None
        self._state = "running"
        self._advance_task(None, generator, "send", None)
    
    def is_alive(self):
        return (self._state in ("running", "paused"))

    def is_paused(self):
        return (self._state in ("paused"))
    
    def join(self, looptime=0.1):
        loop = gobject.MainLoop()
        context = loop.get_context()
        while self._state != "finished":
            context.iteration(False)
            time.sleep(looptime)        
        
    def pause(self):
        self._check_state("running")
        self.current_task.pause()
        self._state = "paused"

    def resume(self):
        self._check_state("paused")
        self.current_task.resume()
        self._state = "running"
        if self._paused_task:
            self._advance_task(*self._paused_task)
            self._paused_task = None
        
    def cancel(self):
        self._check_state("running", "paused")
        self.current_task.cancel()
        self.current_task = None
        for generator in reversed(self.generators):
            generator.close()
        self._state = "cancelled"

    def _start_task(self, task, generator):
        self.current_task = task
        task.config(functools.partial(self._advance_task, task, generator, "send"), 
            functools.partial(self._advance_task, task, generator, "throw"))
        task.run()
        self._state = "running"

    def _advance_task(self, task, generator, method, result=None):
        # Instead of advancing the task/coroutine right away, we defer 
        # the operation so it's run away from propagate_exceptions() that
        # could catches exceptions in the coroutine
        if task != self.current_task:
            raise TaskError("only the current task can reply to the coroutine")                
        if self._state == "running":
            gobject.idle_add(self._advance_task_cb, generator, method, result)
        elif self._state == "paused":
            self._paused_task = (task, generator, method, result)
        
    def _advance_task_cb(self, generator, method, result):
        self.current_task = None
        while 1:
            try:
                new_task_or_generator = getattr(generator, method)(result)
            except StopIteration:
                self.generators.remove(generator)
                generator.close()
                if not self.generators:
                    self._state = "finished"
                    return False
                generator = self.generators[-1]
                method, result = "send", None
                continue                
            except:
                self._state = "finished" # maybe "error"?
                raise
            if isinstance(new_task_or_generator, types.GeneratorType):
                generator = new_task_or_generator
                self.generators.append(generator)
                method, result = "send", None
                continue
            elif isinstance(new_task_or_generator, Task):
                task = new_task_or_generator
                break
            else:
                self.generators.remove(generator)
                generator.close()
                if not self.generators:
                    raise RuntimeError, "Stack has no generators" 
                generator = self.generators[-1]
                method, result = "send", new_task_or_generator
        self._start_task(task, generator)
        return False                    
                
    def _check_state(self, *expected):
        if self._state not in expected:
            msg = "Current job state is '%s', expected was '%s'" % \
                (self._state, "/".join(expected))
            raise ValueError, msg

### Tasks

def propagate_exceptions(method_or_task):
    """
    Decorator to wrap task callbacks (either methods or functions).
    
    This decorator ensures that exceptions raised inside asynchronous
    callbacks of a task are propagated to the coroutine, otherwise the 
    task would simply die resulting on a forever-stuck job.
    """  
    def _propagate_wrapper(task, function, *args, **kwargs):
        try:            
            return function(*args, **kwargs)
        except Exception, exc:
            task.exception_cb(exc)
            raise
    if callable(method_or_task):
        method = method_or_task
        def _wrapper(task, *args, **kwargs):
            return _propagate_wrapper(task, method, task, *args, **kwargs)
        return _wrapper
    elif isinstance(method_or_task, Task):
        task = method_or_task
        def _decorator(function):
            def _wrapper(*args, **kwargs):
                return _propagate_wrapper(task, function, *args, **kwargs)
            return _wrapper
        return _decorator
    else:
        raise ValueError, "Argument should be either a Task method or a Task instance"

class Task:
    """
    Base class for asynchronous tasks.
    
    Tasks must override method run and, optionally, cancel, pause and resume.
    To develop robust tasks, make sure that all asynchronous callbacks that 
    may raise an exception are decorated with propagate_exceptions. 
    """
    def config(self, return_cb, exception_cb):
        self.return_cb = return_cb
        self.exception_cb = exception_cb

    def run(self):
        raise RuntimeError, "Run method must be overriden"

    def cancel(self):
        pass
        
    def pause(self):
        pass

    def resume(self):
        pass
    
# Some ideas for threaded classes:
#
# - ThreadedEventTask: function has cancel and pause event arguments and can
#                      respond to these events.        
# - ThreadedGeneratorTask: run a generator instead of a normal function and 
#                          call a callback for each yielded value
                       
class ThreadedTask(Task):
    """
    Run a function in a new thread and return the result.
    
    Function being run knows nothing about threads nor events, so there is no
    way to cancel it or pause it. So the class does not implement these methods 
    either.    
    """
    def __init__(self, fun, *args, **kwargs):
        self.function = (fun, args, kwargs)

    def run(self):
        queue = Queue()        
        thread = Thread(target=self._thread_manager, args=(self.function, queue))
        thread.setDaemon(True)
        thread.start()
        self.source_id = gobject.timeout_add(50, self._thread_receiver, queue)        
    
    @propagate_exceptions
    def _thread_receiver(self, queue):
        if queue.empty():
            if not thread.isAlive():
                self.exception_cb(TaskError("thread is dead but the queue is empty"))
                return False            
            return True                
        rtype, rvalue = queue.get()
        if rtype == "return":
            self.return_cb(rvalue)
        else:
            self.exception_cb(rvalue)
        return False

    def _thread_manager(self, function, queue):
        fun, args, kwargs = function
        try:
            result = fun(*args, **kwargs)
        except Exception, exc:
            queue.put(("exception", exc))
            raise
        queue.put(("return", result))

            
class SleepTask(Task):
    """Sleep for some time and return."""
    def __init__(self, seconds):
        self.seconds = seconds
        
    def run(self):
        self.source_id = gobject.timeout_add(int(self.seconds * 1000), self._return)
        self.start_time = time.time()
        self.elapsed_time = 0.0

    def cancel(self):
        gobject.source_remove(self.source_id)

    def pause(self):
        gobject.source_remove(self.source_id)        
        self.elapsed_time += time.time() - self.start_time

    def resume(self):
        remaining_time = self.seconds - self.elapsed_time
        self.source_id = gobject.timeout_add(int(remaining_time * 1000), self._return)
        self.start_time = time.time()
        
    def _return(self):
        self.return_cb()
        return False              

def build_request(url, postdata=None):
    """Build a URL request with (optional) POST data"""
    data = (urllib.urlencode(postdata) if postdata else None)
    return urllib2.Request(url, data)

def connect_opener(url, opener=None, headers=None):
    """Connect an opener to a url and return (response, content-length)."""
    opener = opener or urllib2.build_opener() 
    request = (url if isinstance(url, urllib2.Request) else build_request(url))
    for key, value in (headers or {}).iteritems():
        request.add_header(key, value)
    response = opener.open(request)
    content_length = response.headers.getheaders("Content-Length")
    return response, (int(content_length[0]) if content_length else None)
    
       
class ProgressDownloadThreadedTask(Task):
    """
    Download a resource given its URL (it uses urllib2.urlopen) with an  
    opener (urllib2.Request object) and some HTTP headers (dictionary),
    and return the downloaded data.
    
    This tasks calls 'elapsed_cb' every time a chunk of data has been 
    downloaded, containing a tuple (elapsed, total) bytes.
    
    Note that total bytes field can only be set if the response
    contains a valid 'Content-Length' header, otherwise it will be None. 
    """
    def __init__(self, url, opener=None, headers=None, elapsed_cb=None, chunk_size=1024):
        self.url = url
        self.opener = opener
        self.headers = headers
        self.elapsed_cb = elapsed_cb
        self.chunk_size = chunk_size
        self.data = StringIO.StringIO()

    def run(self):
        queue = Queue()
        self.pause_event = Event()
        self.cancel_event = Event()
        thread = Thread(target=self._thread_manager, 
            args=(self.url, self.opener, self.headers, self.chunk_size, 
                  queue, self.pause_event, self.cancel_event))
        thread.setDaemon(True)
        thread.start()
        self.current_size = 0
        self._thread_id = gobject.timeout_add(50, self._thread_receiver, queue, thread)        

    def pause(self):
        self.pause_event.set()
    
    def resume(self):
        self.pause_event.clear()

    def cancel(self):
        self.cancel_event.set()
        gobject.source_remove(self._thread_id)
        
    @propagate_exceptions
    def _thread_receiver(self, queue, thread):
        if self.pause_event.isSet():
            return True        
        elif not thread.isAlive() and queue.empty():
            self.exception_cb(TaskError("thread is dead but the queue is empty"))
            return False 
        while not queue.empty():    
            result = queue.get()
            if not result:
                return False
            key = result["key"]
            if key == "restart":
                self.current_size = 0
                if self.elapsed_cb:
                    self.elapsed_cb(self.current_size, result["size"])
                self.data = StringIO.StringIO()
            elif key == "exception":
                self.exception_cb(result["exception"])
                return False
            elif key == "data":
                self.current_size += len(result["data"])
                if self.elapsed_cb:
                    self.elapsed_cb(self.current_size, result["size"])
                if result["data"]:
                    self.data.write(result["data"])
                else:
                    self.return_cb(self.data.getvalue())
                    return False
            else:
                raise ValueError("Unexpected message in queue")
        return True

    def _thread_manager(self, url, opener, headers, chunk_size, queue, 
            pause_event, cancel_event):
        try:
            request, size = connect_opener(url, opener, headers)
            while 1:                
                data = request.read(chunk_size)
                if cancel_event.isSet():
                    queue.put(None)
                    return
                elif pause_event.isSet():
                    # on pause, close current request and re-connect later
                    request.close()
                    while pause_event.isSet():
                        if cancel_event.isSet():
                            queue.put(None)
                            return
                        time.sleep(0.1)
                    queue.put(dict(key="restart", size=size))
                    request, size = connect_opener(url, opener, headers)
                    continue
                queue.put(dict(key="data", data=data, size=size))
                if not data:
                    break
        except Exception, exc:
            queue.put(dict(key="exception", exception=exc))
            raise
