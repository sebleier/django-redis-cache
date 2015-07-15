from bisect import insort, bisect
from hashlib import md5
from math import log
import sys
from functools import total_ordering

try:
    maxint = sys.maxint
except AttributeError:
    maxint = sys.maxsize

DIGITS = int(log(maxint) / log(16))


def make_hash(s):
    return int(md5(s.encode('utf-8')).hexdigest()[:DIGITS], 16)


@total_ordering
class Node(object):
    def __init__(self, node, i):
        self._node = node
        self._i = i
        self._position = make_hash("{0}:{1}".format(i, self._node))

    def __lt__(self, other):
        if isinstance(other, int):
            return self._position < other
        elif isinstance(other, Node):
            return self._position < other._position
        raise TypeError(
            'Cannot compare this class with "%s" type' % type(other)
        )

    def __eq__(self, other):
        if isinstance(other, int):
            return self._node == other
        elif isinstance(other, Node):
            return self._node == other._node
        raise TypeError(
            'Cannot compare this class with "%s" type' % type(other)
        )


class HashRing(object):

    def __init__(self, replicas=16):
        self.replicas = replicas
        self._nodes = []

    def _add(self, node, i):
        insort(self._nodes, Node(node, i))

    def add(self, node, weight=1):
        for i in range(weight * self.replicas):
            self._add(node, i)

    def remove(self, node):
        n = len(self._nodes)
        for i, _node in enumerate(reversed(self._nodes)):
            if node == _node._node:
                del self._nodes[n - i - 1]

    def get_node(self, key):
        i = bisect(self._nodes, make_hash(key)) - 1
        return self._nodes[i]._node
