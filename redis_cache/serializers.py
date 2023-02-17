try:
    import cPickle as pickle
except ImportError:
    import pickle

import json

try:
    import msgpack
except ImportError:
    pass

try:
    import yaml
except ImportError:
    pass

try:
    import lzma
except ImportError:
    pass

from django.utils.encoding import force_bytes, force_str


class BaseSerializer(object):
    def serialize(self, value):
        raise NotImplementedError

    def deserialize(self, value):
        raise NotImplementedError


class CompressedMixin:
    def serialize(self, value):
        return lzma.compress(force_bytes(super(CompressedMixin, self).serialize(value)))

    def deserialize(self, value):
        return super(CompressedMixin, self).deserialize(lzma.decompress(value))


class PickleSerializer(object):
    def __init__(self, pickle_version=-1):
        self.pickle_version = pickle_version

    def serialize(self, value):
        return pickle.dumps(value, self.pickle_version)

    def deserialize(self, value):
        return pickle.loads(force_bytes(value))


class CompressedPickleSerializer(CompressedMixin, PickleSerializer):
    pass


class JSONSerializer(BaseSerializer):
    def serialize(self, value):
        return force_bytes(json.dumps(value))

    def deserialize(self, value):
        return json.loads(force_str(value))


class CompressedJSONSerializer(CompressedMixin, JSONSerializer):
    pass


class MSGPackSerializer(BaseSerializer):
    def serialize(self, value):
        return msgpack.dumps(value)

    def deserialize(self, value):
        return msgpack.loads(value, encoding="utf-8")


class CompressedMSGPackSerializer(CompressedMixin, MSGPackSerializer):
    pass


class YAMLSerializer(BaseSerializer):
    def serialize(self, value):
        return yaml.dump(value, encoding="utf-8", Dumper=yaml.Dumper)

    def deserialize(self, value):
        return yaml.load(value, Loader=yaml.FullLoader)


class CompressedYAMLSerializer(CompressedMixin, YAMLSerializer):
    pass


class DummySerializer(BaseSerializer):
    def serialize(self, value):
        return value

    def deserialize(self, value):
        return value
