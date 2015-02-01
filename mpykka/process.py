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
# Last modified: Sun Feb  1 22:49:02 2015 mstenber
# Edit time:     126 min
#
"""

multiprocessing-driven Process

"""

from . import actor
from . import registry

import multiprocessing
import threading
import sys

import logging
_debug = logging.getLogger(__name__).debug

# Note: These have to map 1:1 to *Handler method names/signatures!
OP_STOP='stop'
OP_START_ACTOR='start_actor' # rid, cl, a, kwa
OP_QUEUE='queue' # rid, id, (actor_opcode, ..)
OP_RESULT='result' # rid, (is_ok, v..)
OP_ACTOR_DEAD='died' # id

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

class QueueHandler:
    running = True
    rid = 0
    def __init__(self, q, q2):
        self.q = q
        self.q2 = q2
        self.ops = {}
    def _rqueue(self, *data):
        _debug('_queue %s', data)
        self.q2.put(data)
    def _rrun(self, opcode, *data):
        _debug('_run')
        self.rid += 1
        rid = self.rid
        r = actor.Future()
        self.ops[rid] = r
        self._rqueue(opcode, rid, *data)
        return r
    def _loop(self):
        while self.running:
            op = self.q.get()
            _debug('%s got %s', self, op)
            code = op[0]
            fun = getattr(self, code, None)
            if fun is None:
                raise NotImplementedError('%s unknown opcode %s', self, code)
            fun(*op[1:])
    # Messages (no underscore)
    def stop(self):
        self.running = False
    def queue(self, rid, id, data):
        data = list(data)
        if rid:
            data[1:1] = [RemoteFuture(self.q2, rid)]
        else:
            data[1:1] = [None]
        a = registry.get_local_actor_by_id(id)
        a._queue(*data)
    def result(self, rid, rv):
        self.ops[rid]._q.put(rv)
        del self.ops[rid]


class SlaveRequestHandler(QueueHandler):
    def start_actor(self, rid, cl, a, kwa):
        o = cl.start(*a, **kwa)
        self.q2.put((OP_RESULT, rid, (True, o.id)))

def _inproc_main(pid, q1, q2):
    registry.set_id(pid)
    srh = SlaveRequestHandler(q1, q2)
    registry.add_process(srh, 0)
    srh._loop()


class Process(actor.Actor):
    i = 0
    def on_start(self):
        q1 = multiprocessing.Queue()
        q2 = multiprocessing.Queue()
        p = multiprocessing.Process(target=_inproc_main, args=(id(self), q1, q2))
        self.__dict__.update(dict(_q1=q1, _q2=q2, _p=p))
        # q1 == slave process input queue
        # q2 = _our_ input queue
        mrh = QueueHandler(q2, q1)
        t = threading.Thread(target=mrh._loop)
        self.__dict__.update(dict(_rqueue=mrh._rqueue, _rrun=mrh._rrun))
        t.start()
        p.start()
        registry.add_process(self)
    def on_stop(self):
        _debug('Process.on_stop')
        self._q1.put((OP_STOP, ))
        self._q2.put((OP_STOP, ))
        self._p.join()
        registry.remove_process(self)
    def start_actor(self, cl, *a, **kwa):
        _debug('Process.start_actor')
        nid = self._rrun(OP_START_ACTOR, cl, a, kwa).get()
        _debug(' => %s', repr(nid))
        return actor.ActorRef(nid)

