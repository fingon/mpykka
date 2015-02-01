#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: actor.py $
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Copyright (c) 2015 Markus Stenberg
#
# Created:       Sun Feb  1 15:09:05 2015 mstenber
# Last modified: Sun Feb  1 20:46:50 2015 mstenber
# Edit time:     79 min
#
"""

Very much copy of pykka.actor :-)

"""

# Actor queue operations
OP_MSG='msg' # msg
OP_CALL='call' # fn, a, kw
OP_STOP='stop'
# (all also have 'r')

try:
    import queue
except ImportError:
    import Queue as queue

import sys
import threading

import logging
_debug = logging.getLogger(__name__).debug

class Future:
    # TBD - is passing along exceptions between processes sane?
    _data = None
    def __init__(self):
        self._q = queue.Queue(maxsize=1)
    def get(self):
        if self._data is None:
            self._data = self._q.get()
        _debug('Future is set!')
        if self._data[0]:
            return self._data[1]
        _, cl, v = self._data
        _debug('reraise %s %s', cl, v)
        raise cl(v)
    def set(self, v):
        _debug('Setting future to %s', v)
        self._q.put((True, v))
    def set_exception(self):
        (cl, v, tb) = sys.exc_info()
        _debug('Setting future to %s %s', cl, v)
        self._q.put((False, cl, v))

class Actor:
    alive = True
    def __init__(self):
        self._q = queue.Queue()
    def _start(self, *a, **kwa):
        t = threading.Thread(target=self._loop, args=a, kwargs=kwa)
        t.daemon = True
        t.start()
    def _loop(self, *a, **kwa):
        self.on_start(*a, **kwa)
        while self.alive:
            op = self._q.get()
            _debug('got %s', repr(op))
            code = op[0]
            r = op[1]
            try:
                if code == OP_MSG:
                    msg = op[2]
                    rv = self.on_receive(msg)
                    if r is not None:
                        r.set(rv)
                elif code == OP_CALL:
                    _, _, fn, a, kwa = op
                    rv = getattr(self, fn)(*a, **kwa)
                    r.set(rv)
                elif code == OP_STOP:
                    self.alive = False
                else:
                    raise NotImplementedError('[actor] unknown opcode %s' % code)
            except Exception:
                r and r.set_exception()
        self.on_stop()
        if r is not None:
            r.set(None)
    def on_start(self, *a, **kwa):
        pass
    def on_receive(self, msg):
        pass
    def on_stop(self):
        pass
    @classmethod
    def start(cls, *a, **kwa):
        o = cls()
        o._start(*a, **kwa)
        return ActorRef(o)

class ActorProxy:
    def __init__(self, ref):
        self.__dict__.update(dict(_ref=ref))
    def __getattr__(self, k):
        def _f(*a, **kwa):
            return self._ref.call(k, *a, **kwa)
        self.__dict__[k] = _f
        return _f
    def __setattr__(self, k, v):
        raise NotImplementedError('ActorProxy.__setattr__')

class BaseActorRef:
    def _queue(self, data):
        raise NotImplementedError('BaseActorRef._queue')
    def _queue_r(self, data):
        raise NotImplementedError('BaseActorRef._queue_r')
    def __setattr__(self, k, v):
        raise NotImplementedError('BaseActorRef.__setattr__')
    # Core calls
    def ask(self, msg):
        return self._queue_r(OP_MSG, msg)
    def call(self, fn, *a, **kw):
        return self._queue_r(OP_CALL, fn, a, kw)
    def stop(self):
        return self._queue_r(OP_STOP)
    def tell(self, msg):
        self._queue(OP_MSG, None, msg)
    # Other utilities
    def proxy(self):
        return ActorProxy(self)

class ActorRef(BaseActorRef):
    def __init__(self, a):
        self.__dict__.update(dict(_a=a))
    def _queue(self, *data):
        assert self._a.alive
        self._a._q.put(data)
    def _queue_r(self, opcode, *data):
        r = Future()
        self._queue(opcode, r, *data)
        return r

