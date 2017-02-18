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

import unittest
import os
import time
import gobject
import functools

from pysheng import asyncjobs
from pysheng.yieldfrom import supergenerator, _from


TESTS_DIR = os.path.abspath(os.path.dirname(__file__))


class TestTask(asyncjobs.Task):
    def __init__(self):
        self.state = "running"

    def run(self):
        pass

    def pause(self):
        self.state = "paused"

    def resume(self):
        self.state = "running"

    def cancel(self):
        self.state = "cancelled"

    @asyncjobs.propagate_exceptions
    def do_action(self, action, value=None):
        if action == "return":
            self.return_cb(value)
        elif action == "exception":
            self.exception_cb(value)
        elif action == "runtime-error":
            raise RuntimeError
        else:
            raise ValueError

    def do_action_with_function_decorator(self, exception):
        @asyncjobs.propagate_exceptions(self)
        def _callback():
            raise exception
        _callback()


class State:
    def __init__(self):
        self.job_result = None


def test_job(state, force_continue_after_cancel=False):
    try:
        state.job_result = yield TestTask()
    except asyncjobs.JobCancelled:
        state.job_result = "!cancelled"
        if not force_continue_after_cancel:
            return
    except Exception, ex:
        state.job_result = ex
        return
    try:
        state.job_result2 = yield TestTask()
    except asyncjobs.JobCancelled:
        state.job_result2 = "!cancelled"
    except Exception, ex:
        state.job_result2 = ex


class TestAsyncJobs(unittest.TestCase):
    def setUp(self):
        self.loop = gobject.MainLoop()
        self.context = self.loop.get_context()
        self.state = State()
        self.generator = test_job(self.state)
        self.job = asyncjobs.Job(self.generator)
        self.tick_events()

    def tick_events(self):
        self.context.iteration(False)

    def test_init(self):
        self.assertTrue(self.job.is_alive())
        self.assertEqual("running", self.job.current_task.state)

    def test_run_with_return(self):
        self.job.current_task.do_action(action="return", value="hello")
        self.tick_events()
        self.assertEqual("hello", self.state.job_result)
        self.assertTrue(self.job.is_alive())

    def test_run_with_exception(self):
        self.job.current_task.do_action(action="exception", value=ValueError())
        self.tick_events()
        self.assertEqual(ValueError, type(self.state.job_result))
        self.assertFalse(self.job.is_alive())

    def test_run_second_task_with_return(self):
        self.job.current_task.do_action(action="return", value="hello")
        self.tick_events()
        self.assertEqual("hello", self.state.job_result)
        self.job.current_task.do_action(action="return", value="bye")
        self.tick_events()
        self.assertEqual("bye", self.state.job_result2)
        self.assertFalse(self.job.is_alive())

    def test_pause(self):
        self.job.pause()
        self.assertTrue(self.job.is_alive())
        self.assertTrue(self.job.is_paused())
        self.assertEqual("paused", self.job.current_task.state)

    def test_cancel(self):
        self.job.cancel()
        self.assertFalse(self.job.is_alive())
        self.assertFalse(self.job.current_task)
        self.assertEqual("!cancelled", self.state.job_result)

    def test_cancel_disobedient_job_that_continues_after_being_cancelled(self):
        generator = test_job(self.state, force_continue_after_cancel=True)
        job = asyncjobs.Job(generator)
        self.tick_events()
        self.assertRaises(RuntimeError, job.cancel)

    def test_exception_in_task_is_propagated_to_job_when_using_decorator(self):
        self.assertRaises(RuntimeError,
                          self.job.current_task.do_action, "runtime-error")
        self.tick_events()
        self.assertFalse(self.job.is_alive())
        self.assertEqual(RuntimeError, type(self.state.job_result))

    def test_exception_in_task_is_propagated_on_protected_callback(self):
        self.assertRaises(RuntimeError,
                          self.job.current_task.
                          do_action_with_function_decorator,
                          RuntimeError)
        self.tick_events()
        self.assertFalse(self.job.is_alive())
        self.assertEqual(RuntimeError, type(self.state.job_result))

    def test_paused_and_resume(self):
        self.job.pause()
        self.assertTrue(self.job.current_task)
        self.job.current_task.do_action(action="return", value="hello")
        self.tick_events()
        self.assertEqual(None, self.state.job_result)
        self.job.resume()
        self.tick_events()
        self.assertTrue(self.job.is_alive())
        self.assertFalse(self.job.is_paused())
        self.assertTrue(self.job.current_task)
        self.assertEqual("hello", self.state.job_result)

        self.job.current_task.do_action(action="return", value="bye")
        self.tick_events()
        self.assertEqual("bye", self.state.job_result2)

# Threaded task


def threaded_task(state, loop, fun, *args, **kwargs):
    state.result = None
    state.result = yield asyncjobs.ThreadedTask(fun, *args, **kwargs)


def myfunc(x, y):
    return x + y


class TestThreadedTask(unittest.TestCase):
    def setUp(self):
        self.state = State()
        self.loop = gobject.MainLoop()
        self.job = asyncjobs.Job(threaded_task(self.state, self.loop, myfunc,
                                 2, 3))

    def test_task(self):
        self.job.join()
        self.assertEqual(5, self.state.result)
        self.assertFalse(self.job.is_alive())

# Sleep task


def sleep_task(state, loop, seconds):
    state.result = None
    yield asyncjobs.SleepTask(seconds)


class TestSleepTask(unittest.TestCase):
    def setUp(self):
        self.state = State()
        self.loop = gobject.MainLoop()
        self.job = asyncjobs.Job(sleep_task(self.state, self.loop, 0.11))

    def test_task(self):
        itime = time.time()
        self.job.join()
        elapsed = time.time() - itime
        self.assert_(elapsed >= 0.10)
        self.assertFalse(self.job.is_alive())

# Threaded progress download task


def threaded_task(state, loop, url):
    state.result = None
    cb = functools.partial(elapsed_cb, state)
    state.callback = []
    state.result = \
        yield asyncjobs.ProgressDownloadThreadedTask(url, elapsed_cb=cb)


def elapsed_cb(state, elapsed, total):
    state.callback.append((elapsed, total))


class TestThreadedTask(unittest.TestCase):
    def setUp(self):
        self.state = State()
        self.loop = gobject.MainLoop()
        self.filepath = os.path.abspath(__file__)
        self.url = "file://" + self.filepath
        self.job = asyncjobs.Job(threaded_task(self.state, self.loop,
                                 self.url))

    def test_task(self):
        self.job.join()
        data = open(self.filepath).read()
        self.assertEqual(data, self.state.result)
        self.assertFalse(self.job.is_alive())
        for elapsed, total in self.state.callback:
            self.assertTrue(total, len(data))
        elapsed_total, total = self.state.callback[-1]
        self.assertEqual(len(data), elapsed_total)


if __name__ == '__main__':
    unittest.main()
