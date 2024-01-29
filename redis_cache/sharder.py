import hashlib
from bisect import insort, bisect


DIGITS = 8


def get_slot(key):
    digest = hashlib.md5(key.encode('utf-8')).hexdigest()
    return int(digest[-DIGITS:], 16)


class Node:

    def __init__(self, node, i):
        self._node = node
        self._i = i
        key = f"{i}:{self._node}"
        self._position = get_slot(key)

    def __gt__(self, other):
        if isinstance(other, int):
            return self._position > other
        elif isinstance(other, Node):
            return self._position > other._position
        raise TypeError(
            'Cannot compare this class with "%s" type' % type(other)
        )


class HashRing:

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
        i = bisect(self._nodes, get_slot(key)) - 1
        return self._nodes[i]._node
