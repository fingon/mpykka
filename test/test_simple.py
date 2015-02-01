#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: test_simple.py $
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Copyright (c) 2015 Markus Stenberg
#
# Created:       Sun Feb  1 15:10:53 2015 mstenber
# Last modified: Sun Feb  1 22:33:40 2015 mstenber
# Edit time:     24 min
#
"""

"""

from mpykka import Actor, Process

import logging
_debug = logging.getLogger(__name__).debug

class DummyException(Exception):
    pass

class DummyActor(Actor):
    def on_receive(self, value):
        if value is None:
            raise DummyException
        _debug('on_message')
        return value
    def fun(self, *value, **kw):
        return value, kw
    def err(self):
        raise DummyException

class Echoer(Actor):
    def on_receive(self, a):
        (next, msg) = a
        return next.ask(msg).get()

def test_simple():
    a = DummyActor.start()
    a.tell('foo')
    assert a.ask('foo').get() == 'foo'
    try:
        a.ask(None).get()
        assert None
    except DummyException as e:
        _debug('exception %s', e)
        pass
    p = a.proxy()
    assert p.fun('foo').get() == (('foo',), {})
    try:
        p.err().get()
        assert None
    except DummyException as e:
        _debug('exception %s', e)
        pass
    a.stop()

def test_process():
    p = Process.start()
    a = p.proxy().start_actor(DummyActor).get()
    a.tell('foo')
    assert a.ask('foo').get() == 'foo'
    ap = a.proxy()
    assert ap.fun('foo').get() == (('foo',), {})
    _debug('stopping actor')
    a.stop().get()
    _debug('stopping process')
    p.stop().get()
    _debug('done')

def test_process_2():
    da = DummyActor.start()
    p = Process.start()
    e = p.proxy().start_actor(Echoer).get()
    assert e.ask((da, 'echo')).get() == 'echo'
    _debug('stopping Echoer')
    e.stop().get()
    _debug('stopping sub-process')
    p.stop().get()
    _debug('stopping local actor')
    da.stop().get()
    _debug('done')

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    #test_simple()
    #test_process()
    test_process_2()
