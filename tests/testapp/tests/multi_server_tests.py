from collections import Counter
from math import sqrt
from redis_cache.sharder import HashRing


def mean(lst):
    return sum(lst) / len(lst)


def stddev(lst):
    """returns the standard deviation of lst"""
    avg = mean(lst)
    variance = sum((i - avg) ** 2 for i in lst)
    return sqrt(variance)


class MultiServerTests(object):

    def test_distribution(self):
        nodes = [node._position for node in self.cache.sharder._nodes]
        nodes.sort()
        diffs = [(b - a) for a, b in zip(nodes[:-1], nodes[1:])]
        l = 16 ** 8
        perfect_dist = l / len(nodes)
        random_dist = sum(diffs) / len(diffs)
        _max = max([perfect_dist, random_dist])
        _min = min([perfect_dist, random_dist])
        percentage = (1 - _max / _min) * 100

        # Assert they are less than 2 percent of each other
        self.assertLess(percentage, 2.0)

    def test_make_key_distribution(self):
        ring = HashRing()
        nodes = set([str(node._node) for node in self.cache.sharder._nodes])
        nodes = [
            ('127.0.0.1', 6379, 15, '/tmp/redis0.sock'),
            ('127.0.0.1', 6379, 15, '/tmp/redis1.sock'),
            ('127.0.0.1', 6379, 15, '/tmp/redis2.sock'),
        ]
        for node in nodes:
            ring.add(str(node))

        n = 50000
        counter = Counter(
            [ring.get_node(str(i)) for i in range(n)]
        )
        self.assertLess(
            ((stddev(counter.values()) / n) * 100.0), 10, counter.values()
        )

    def test_key_distribution(self):
        n = 10000
        for i in range(n):
            self.cache.set(i, i)
        keys = [
            len(client.keys('*'))
            for client in self.cache.clients.values()
        ]
        self.assertEqual(sum(keys), n)
        self.assertLess(((stddev(keys) / n) * 100.0), 10)

    def test_removing_nodes(self):
        c1, c2, c3 = self.cache.clients.keys()
        replicas = self.cache.sharder.replicas

        self.assertEqual(len(self.cache.sharder._nodes), 3 * replicas)

        self.cache.sharder.remove(c1)
        self.assertEqual(len(self.cache.sharder._nodes), 2 * replicas)

        self.cache.sharder.remove(c2)
        self.assertEqual(len(self.cache.sharder._nodes), 1 * replicas)

        self.cache.sharder.remove(c3)
        self.assertEqual(len(self.cache.sharder._nodes), 0)
