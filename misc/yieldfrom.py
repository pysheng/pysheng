#!/usr/bin/python
"""Pure Python implementation of PEP-380 (yield from)."""
from functools import wraps
import types

class _from(object):
    """Wrap a nested generator call in a supergenerator."""
    def __init__(self, genfunc):
        self.genfunc = genfunc

def supergenerator(genfunc, require_from=True):
    """
    Decorate a generator so it can yield nested generators (using class _from).

    @supergenerator
    def mysupergen():
        yield "normal yield"
        yield "one more yield"
        yield _from(othergen())
        yield _from(yet_othergen())
        yield "last yield"

    Note that nested generators can, in turn, yield other generators. Nested
    generators do not have to use the decorator.
    """
    def _process(gen):
        tosend = None
        while 1:
            yielded = gen.send(tosend)
            if (isinstance(yielded, _from) or
                  (not require_from and isinstance(yielded, types.GeneratorType))):
                nested_gen = _process(yielded.genfunc if isinstance(yielded, _from)
                                      else yielded)
                nested_tosend = None
                while 1:
                    try:
                        nested_yielded = nested_gen.send(nested_tosend)
                    except StopIteration, exc:
                        new_tosend = (exc.args[0] if exc.args else None)
                        break
                    except Exception, exc:
                        yielded.genfunc.close()
                        yielded2 = gen.throw(exc)
                        new_tosend = (yield yielded2)
                        break
                    nested_tosend = (yield nested_yielded)
            else:
                new_tosend = (yield yielded)
            tosend = new_tosend
    @wraps(genfunc)
    def _wrapper(*args, **kwargs):
        return _process(genfunc(*args, **kwargs))
    return _wrapper
