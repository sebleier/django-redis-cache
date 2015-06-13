from math import sqrt


def mean(lst):
    return sum(lst) / len(lst)


def stddev(lst):
    """returns the standard deviation of lst"""
    avg = mean(lst)
    variance = sum((i - avg) ** 2 for i in lst)
    return sqrt(variance)


class MultiServerTests(object):

    def test_key_distribution(self):
        n = 10000
        for i in xrange(n):
            self.cache.set(i, i)
        keys = [len(client.keys('*')) for client in self.cache.clients.itervalues()]
        self.assertTrue(((stddev(keys) / n) * 100.0) < 10)

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
