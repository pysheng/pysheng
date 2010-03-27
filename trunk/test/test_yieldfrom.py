#!/usr/bin/python
import unittest
import StringIO
import sys
import os
import types

from pysheng.yieldfrom import supergenerator, _from

# Generators

@supergenerator
def normal_generator():
  yield "1"; yield "2"; yield gen2()
  
@supergenerator  
def gen1():
  yield "1a"; yield "2a"
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

def coro2_with_no_return(coro3, s):
    yield "start-coro2"
    value = yield _from(coro3(s))

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

def coro2_with_catch(coro3, s):
    yield "start-coro2"
    try:
        value = yield _from(coro3(s))
    except ValueError:
        yield "coro2-catch-%s" % s
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
    def setUp(self):
        pass
    
    def test_normal_generator(self):
        result = list(normal_generator())
        self.assertEqual(["1", "2"], result[:2])
        generator = result[-1]
        self.assert_(isinstance(generator, types.GeneratorType))
        self.assert_("gen2", generator.__name__)

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
        self.assertEqual(None, coro.send(None))
        self.assertEqual("start-coro2", coro.send(None))
        self.assertEqual("start-coro3", coro.send(None))
        self.assertEqual("coro3-start-there-0", coro.send(None))
        self.assertEqual("coro3-20-there-1", coro.send(20))
        self.assertEqual(None, coro.send(None))
        self.assertEqual("end-coro1", coro.send(None))
        self.assertRaises(StopIteration, coro.send, None)

    def test_nested_coroutine_with_catch_on_inmediate_level_above_raise(self):
        coro = coro1(coro2_with_catch, coro3_with_exception)
        self.assertEqual("start-coro1", coro.send(None))
        self.assertEqual("start-coro2", coro.send(None))
        self.assertEqual("start-coro3", coro.send(None))
        self.assertEqual("coro2-catch-hello", coro.send(None))
        self.assertEqual("end-coro2", coro.send(None))
        self.assertEqual("start-coro2", coro.send(None))
        self.assertEqual("start-coro3", coro.send(None))
        self.assertEqual("coro2-catch-there", coro.send(None))
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
