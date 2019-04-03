import numpy as np
import torch

from .types import BasicType, validate_class, BSON, JSON


class _Tensor(BasicType):
    def __init__(self, *, klass=torch.Tensor, **kwargs):
        super().__init__(klass=klass, **kwargs)

    def _to_jsony(self, value, target):
        validate_class(value, self.klass)
        value = value.numpy()
        if target is JSON:
            return value.tolist()
        elif target is BSON:
            return {
                "shape": value.shape,
                "content": value.tobytes(),
            }
        else:
            raise ValueError(f"Unsupported target {target}")

    def _from_jsony(self, jsony, source):
        if source is JSON or isinstance(jsony, list):
            validate_class(jsony, list)
            return torch.from_numpy(np.array(jsony, dtype=np.float32))
        elif source is BSON:
            validate_class(jsony, dict)
            validate_class(jsony['content'], bytes)
            validate_class(jsony['shape'], list)
            value = np.fromstring(jsony['content'], dtype=np.float32)
            return torch.from_numpy(value).view(*jsony['shape'])
        else:
            raise ValueError(f"Unsupported source {source}")


Tensor = _Tensor()


class _FloatOrTensor(BasicType):
    def __init__(self, *, klass=float, **kwargs):
        super().__init__(klass=klass, **kwargs)

    @property
    def name(self):
        return "FloatOrTensor"

    def _to_jsony(self, value, target):
        if isinstance(value, (int, float)):
            return float(value)
        else:
            return Tensor.to_jsony(value, target)

    def _from_jsony(self, value, source):
        if isinstance(value, (int, float)):
            return value
        else:
            return Tensor.from_jsony(value, source)


FloatOrTensor = _FloatOrTensor()
