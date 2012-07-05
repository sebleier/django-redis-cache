from hashlib import sha1
import bisect
from django.utils.encoding import smart_unicode, smart_str
HEX_DIGITS = 7
MAX_NODES = 16**HEX_DIGITS


class Node(object):
    def __init__(self, client, value, id):
        self.value = value
        self._client = client
        self.id = id

    def __repr__(self):
        return "<Node: value=%s>" % self.value

    def __cmp__(self, x):
        if isinstance(x, Node):
            return cmp(self.value, x.value)
        else:
            return cmp(self.value, x)

    def __eq__(self, other):
        if isinstance(other, Node):
            return self.id == other.id
        else:
            return self.id == other


class Interval(object):
    """
    Simple data structure to hold the start and end values of a keyspace
    interval.
    """
    def __init__(self, start, end):
        self.start, self.end = start, end

    def __repr__(self):
        return "[%s, %s]" % (self.start, self.end)

    @property
    def length(self):
        return self.end - self.start

    def __cmp__(self, other):
        return cmp(self.length, other.length)


class CacheSharder(object):

    def __init__(self, clients=[]):
        self._clients = []
        self.intervals = []

    def __len__(self):
        return len(self._clients)

    def add(self, client, id):
        """
        Adds client to the sorted client list.

        Uses the sorted interval list to find the largest one available.  Pop
        that interval and split it into two equal pieces and place back into
        the list and resort.  The client value will be the bisect of the popped
        interval.
        """
        if len(self.intervals) == 0:
            self.intervals.append(Interval(0, 1))
            value = 0.0
        else:
            interval = self.intervals.pop()
            value = interval.start + (interval.end - interval.start) / 2.0
            # Create two half-sized intervals and push back into the list
            left, right = Interval(interval.start, value), Interval(value, interval.end)
            self.intervals.append(left)
            self.intervals.append(right)
            self.intervals.sort()
        #insert the client
        bisect.insort_left(self._clients, Node(client, value, id))

    def remove(self, server):
        """
        Removes a client using the id.

        Finds adjacent intervals and combines them before removing client from
        the
        """
        i = self._clients.index(server)
        client = self._clients[i]
        left, = filter(lambda x: x.end == client.value, self.intervals)
        right, = filter(lambda x: x.start == client.value, self.intervals)

        self.intervals.append(Interval(left.start, right.end))
        self.intervals.remove(left)
        self.intervals.remove(right)
        self.intervals.sort()
        self._clients.remove(client)

    def get_position(self, key):
        return int(sha1(smart_str(key)).hexdigest()[:HEX_DIGITS], 16) / float(MAX_NODES)

    def get_client(self, key):
        position = self.get_position(key)
        index = bisect.bisect(self._clients, position) - 1
        return self._clients[index]._client
