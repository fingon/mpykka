#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: process.py $
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Copyright (c) 2015 Markus Stenberg
#
# Created:       Sun Feb  1 16:27:22 2015 mstenber
# Last modified: Sun Feb  1 20:47:53 2015 mstenber
# Edit time:     66 min
#
"""

multiprocessing-driven Process

"""

from . import actor
import multiprocessing
import threading
import sys

import logging
_debug = logging.getLogger(__name__).debug

# master -> slave process
OP_STOP='stop'
OP_START_ACTOR='start' # id, cl, a, kwa
OP_QUEUE='queue' # id, (actor_opcode, ..)
# (all have rid as second argument before optional arguments)

# slave -> master process
OP_RESULT='result' # rid, (is_ok, v..)
OP_ACTOR_DEAD='died' # id
# (+ OP_STOP from self)

class RemoteFuture:
    def __init__(self, q, rid):
        self._q = q
        self._rid = rid
    def set(self, v):
        _debug('RemoteFuture.set %s', v)
        self._q.put((OP_RESULT, self._rid, (True, v)))
    def set_exception(self):
        _debug('RemoteFuture.set_exception')
        (cl, v, tb) = sys.exc_info()
        self._q.put((OP_RESULT, self._rid, (False, cl, v)))

def _inproc_main(q1, q2):
    running = {}
    while True:
        op = q1.get()
        code = op[0]
        if code == OP_START_ACTOR:
            _, rid, i, cl, a, kwa = op
            o = cl.start(*a, **kwa)
            running[i] = o
            q2.put((OP_RESULT, rid, (True, None)))
        elif code == OP_QUEUE:
            _, rid, id, data = op
            data = list(data)
            if rid:
                data[1:1] = [RemoteFuture(q2, rid)]
            else:
                data[1:1] = [None]
            running[i]._queue(*data)
        elif code == OP_STOP:
            break
        else:
            raise NotImplementedError('[slave] unknown opcode %s', code)

class Process(actor.Actor):
    i = 0
    rid = 0
    def _queue(self, *data):
        self._q1.put(data)
    def _loop_read_from_remote(self):
        while True:
            op = self._q2.get()
            _debug('_loop_read_from_remote: %s', op)
            code = op[0]
            if code == OP_RESULT:
                _, rid, d = op
                self._ops[rid]._q.put(d)
                del self._ops[rid]
            elif code == OP_ACTOR_DEAD:
                # N/A yet?
                pass
            elif code == OP_STOP:
                break
            else:
                raise NotImplementedError('[process] unknown opcode %s', code)

    def _run(self, opcode, *data):
        self.rid += 1
        rid = self.rid
        r = actor.Future()
        self._ops[rid] = r
        self._queue(opcode, rid, *data)
        return r
    def on_start(self):
        q1 = multiprocessing.Queue()
        q2 = multiprocessing.Queue()
        p = multiprocessing.Process(target=_inproc_main, args=(q1, q2))
        t = threading.Thread(target=self._loop_read_from_remote)
        self.__dict__.update(dict(_q1=q1, _q2=q2, _p=p, _t=t, _ops={}))
        t.start()
        p.start()
    def on_stop(self):
        _debug('Process.on_stop')
        self._q1.put((OP_STOP, ))
        self._q2.put((OP_STOP, ))
        self._p.join()
    def start_actor(self, cl, *a, **kwa):
        _debug('Process.start_actor')
        self.i += 1
        i = self.i
        self._run(OP_START_ACTOR, i, cl, a, kwa).get() # No exception -> ok
        return RemoteRef(self, i)

class RemoteRef(actor.BaseActorRef):
    def __init__(self, p, i):
        self.__dict__.update(dict(_p=p, _i=i))
    def _queue(self, *data):
        _debug('RemoteRef._queue %s', data)
        self._p._queue(OP_QUEUE, None, self._i, data)
    def _queue_r(self, *data):
        _debug('RemoteRef._queue_r %s', data)
        return self._p._run(OP_QUEUE, self._i, data)

