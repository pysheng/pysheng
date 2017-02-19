#!/usr/bin/python
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pysheng.yieldfrom import supergenerator, _from

# Generators


@supergenerator
def normal_generator(gen):
    yield "1"
    yield "2"
    yield gen()
    yield "3"


@supergenerator
def gen1():
    """My docstring"""
    yield "1a"
    yield "2a"
    yield _from(gen2())
    yield "3a"


def gen2():
    yield "2a"
    yield _from(gen3())
    yield "2b"


def gen3():
    yield "3a"
    yield "3b"

# Coroutines


@supergenerator
def coro1(coro2, coro3):
    yield "start-coro1"
    value = yield _from(coro2(coro3, "hello"))
    yield value
    value = yield _from(coro2(coro3, "there"))
    yield value
    yield "end-coro1"


def coro2(coro3, s):
    yield "start-coro2"
    value = yield _from(coro3(s))
    yield value
    raise StopIteration("end-coro2")


def coro3(s):
    yield "start-coro3"
    value = "start"
    for i in range(2):
        value = yield "coro3-%s-%s-%d" % (value, s, i)
    raise StopIteration("end-coro3")

# Coroutines variations


@supergenerator
def coro1_with_catch(coro2, coro3):
    yield "start-coro1"
    try:
        value = yield _from(coro2(coro3, "hello"))
        yield value
    except ValueError:
        yield "coro1-catch-hello"
    try:
        value = yield _from(coro2(coro3, "there"))
        yield value
    except ValueError:
        yield "coro1-catch-there"
    yield "end-coro1"


def coro2_with_no_return(coro3, s):
    yield "start-coro2"
    value = yield _from(coro3(s))
    yield value


def coro2_with_catch(coro3, s):
    yield "start-coro2"
    try:
        value = yield _from(coro3(s))
    except ValueError:
        value = yield "coro2-catch-%s" % s
        yield "coro2-catch-%s" % value
    raise StopIteration("end-coro2")


def coro3_with_exception(s):
    yield "start-coro3"
    value = "start"
    raise ValueError
    for i in range(2):
        value = yield "coro3-%s-%s-%d" % (value, s, i)
    raise StopIteration("end-coro3")

#####


class TestYieldFrom(unittest.TestCase):
    def test_decorator_keeps_docstrings(self):
        self.assertEqual("My docstring", gen1.__doc__)

    def test_normal_generator(self):
        result = list(normal_generator(gen2))
        self.assertEqual(4, len(result))
        self.assertEqual(["1", "2", "3"], result[:2] + result[-1:])
        generator = result[-2]
        self.assertTrue(isinstance(generator, types.GeneratorType))
        self.assertEqual("gen2", generator.__name__)

    def test_nested_generator(self):
        result = list(gen1())
        self.assertEqual(['1a', '2a', '2a', '3a', '3b', '2b', '3a'], result)

    def test_nested_coroutine(self):
        coro = coro1(coro2, coro3)
        self.assertEqual("start-coro1", coro.send(None))
        self.assertEqual("start-coro2", coro.send(None))
        self.assertEqual("start-coro3", coro.send(None))
        self.assertEqual("coro3-start-hello-0", coro.send(None))
        self.assertEqual("coro3-10-hello-1", coro.send(10))
        self.assertEqual("end-coro3", coro.send(None))
        self.assertEqual("end-coro2", coro.send(None))
        self.assertEqual("start-coro2", coro.send(None))
        self.assertEqual("start-coro3", coro.send(None))
        self.assertEqual("coro3-start-there-0", coro.send(None))
        self.assertEqual("coro3-20-there-1", coro.send(20))
        self.assertEqual("end-coro3", coro.send(None))
        self.assertEqual("end-coro2", coro.send(None))
        self.assertEqual("end-coro1", coro.send(None))
        self.assertRaises(StopIteration, coro.send, None)

    def test_nested_coroutine_with_no_return_on_one_nested_coroutine(self):
        coro = coro1(coro2_with_no_return, coro3)
        self.assertEqual("start-coro1", coro.send(None))
        self.assertEqual("start-coro2", coro.send(None))
        self.assertEqual("start-coro3", coro.send(None))
        self.assertEqual("coro3-start-hello-0", coro.send(None))
        self.assertEqual("coro3-10-hello-1", coro.send(10))
        self.assertEqual("end-coro3", coro.send(None))
        self.assertEqual(None, coro.send(None))
        self.assertEqual("start-coro2", coro.send(None))
        self.assertEqual("start-coro3", coro.send(None))
        self.assertEqual("coro3-start-there-0", coro.send(None))
        self.assertEqual("coro3-20-there-1", coro.send(20))
        self.assertEqual("end-coro3", coro.send(None))
        self.assertEqual(None, coro.send(None))
        self.assertEqual("end-coro1", coro.send(None))
        self.assertRaises(StopIteration, coro.send, None)

    def test_nested_coroutine_with_catch_which_yields_the_result_of_thow(self):
        coro = coro1(coro2_with_catch, coro3_with_exception)
        self.assertEqual("start-coro1", coro.send(None))
        self.assertEqual("start-coro2", coro.send(None))
        self.assertEqual("start-coro3", coro.send(None))
        self.assertEqual("coro2-catch-hello", coro.send(None))
        self.assertEqual("coro2-catch-xyz", coro.send("xyz"))
        self.assertEqual("end-coro2", coro.send(None))
        self.assertEqual("start-coro2", coro.send(None))
        self.assertEqual("start-coro3", coro.send(None))
        self.assertEqual("coro2-catch-there", coro.send(None))
        self.assertEqual("coro2-catch-abc", coro.send("abc"))
        self.assertEqual("end-coro2", coro.send(None))
        self.assertEqual("end-coro1", coro.send(None))
        self.assertRaises(StopIteration, coro.send, None)

    def test_nested_coroutine_with_catch_two_levels_above_raise(self):
        coro = coro1_with_catch(coro2, coro3_with_exception)
        self.assertEqual("start-coro1", coro.send(None))
        self.assertEqual("start-coro2", coro.send(None))
        self.assertEqual("start-coro3", coro.send(None))
        self.assertEqual("coro1-catch-hello", coro.send(None))
        self.assertEqual("start-coro2", coro.send(None))
        self.assertEqual("start-coro3", coro.send(None))
        self.assertEqual("coro1-catch-there", coro.send(None))
        self.assertEqual("end-coro1", coro.send(None))
        self.assertRaises(StopIteration, coro.send, None)


if __name__ == '__main__':
    unittest.main()
