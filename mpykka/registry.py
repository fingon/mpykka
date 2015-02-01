#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: registry.py $
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Copyright (c) 2015 Markus Stenberg
#
# Created:       Sun Feb  1 21:08:43 2015 mstenber
# Last modified: Sun Feb  1 22:39:58 2015 mstenber
# Edit time:     11 min
#
"""

"""

import threading

import logging
_debug = logging.getLogger(__name__).debug

# 0 = global default namespace
_id = 0
_id2o = {}
_id2p = {}
_lock = threading.Lock()

def add(o):
    with _lock:
        _id2o[id(o)] = o
        nid = (_id, id(o))
        o.id = nid
    _debug('added %s = %s', nid, o)

def remove(o):
    with _lock:
        del _id2o[id(o)]
    _debug('removed %s', o.id)

def get_local_actor_by_id(id):
    with _lock:
        return _id2o[id]

def get_actor_by_uid(id):
    with _lock:
        if id[0] == _id:
            return _id2o[id[1]]

def get_process_by_id(id):
    with _lock:
        return _id2p[id]

def add_process(p, pid=None):
    with _lock:
        if pid is None:
            pid = id(p)
        _id2p[pid] = p
    _debug('added process %s', p)

def remove_process(p):
    with _lock:
        del _id2p[id(p)]
    _debug('removed process %s', p)

def set_id(id):
    global _id
    _id = id
    _debug('set id %s', id)
