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
# Last modified: Sun Feb  1 22:46:51 2015 mstenber
# Edit time:     110 min
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

from . import registry

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
        _debug('Future.get %s', self._data)
        if self._data[0]:
            return self._data[1]
        _, cl, v = self._data
        raise cl(v)
    def set(self, v):
        _debug('Future.set %s', v)
        self._q.put((True, v))
    def set_exception(self):
        (cl, v, tb) = sys.exc_info()
        _debug('Future.set_exception %s %s', cl, v)
        self._q.put((False, cl, v))

class Actor:
    alive = True
    def __init__(self):
        self._q = queue.Queue()
    def _queue(self, *data):
        assert self.alive
        self._q.put(data)
    def _run(self, opcode, *data):
        r = Future()
        self._queue(opcode, r, *data)
        return r
    def _start(self, *a, **kwa):
        t = threading.Thread(target=self._loop, args=a, kwargs=kwa)
        t.daemon = True
        t.start()
    def _loop(self, f, *a, **kwa):
        self.on_start(*a, **kwa)
        # post on_start, the object is 'ready'
        f.set(None)
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
        registry.remove(self)
    def on_start(self, *a, **kwa):
        pass
    def on_receive(self, msg):
        pass
    def on_stop(self):
        pass
    @classmethod
    def start(cls, *a, **kwa):
        o = cls()
        registry.add(o)
        f = Future()
        o._start(f, *a, **kwa)
        f.get()
        return ActorRef(o.id)

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

class RemoteActor:
    def __init__(self, p, i):
        self.__dict__.update(dict(_p=p, _i=i))
    def _queue(self, *data):
        _debug('RemoteRef._queue %s', data)
        self._p._rqueue('queue', None, self._i, data)
    def _run(self, *data):
        _debug('RemoteRef._run %s', data)
        return self._p._rrun('queue', self._i, data)

class ActorRef:
    def __init__(self, id):
        self.__dict__.update(dict(id=id))
    def _get_actor(self):
        a = getattr(self, 'actor', None)
        if a is None:
            a = registry.get_actor_by_uid(self.id)
            if a is None:
                p = registry.get_process_by_id(self.id[0])
                a = RemoteActor(p, self.id[1])
                _debug('%s _get_actor => remote %s', self, a)
            else:
                _debug('%s _get_actor => local %s', self, a)

            assert a is not None
            self.__dict__['actor'] = a
        return a
    def _queue(self, *data):
        return self._get_actor()._queue(*data)
    def _run(self, *data):
        return self._get_actor()._run(*data)
    def __getstate__(self):
        return {'id': self.id}
    def __setattr__(self, k, v):
        raise NotImplementedError('BaseActorRef.__setattr__')
    # Core calls
    def ask(self, msg):
        return self._run(OP_MSG, msg)
    def call(self, fn, *a, **kw):
        return self._run(OP_CALL, fn, a, kw)
    def stop(self):
        return self._run(OP_STOP)
    def tell(self, msg):
        self._queue(OP_MSG, None, msg)
    # Other utilities
    def proxy(self):
        return ActorProxy(self)

