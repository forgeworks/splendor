

@system.adapter("object", "dict")
class ObjectDictAdapter:
    def __init__(self, instance):
        self.instance = instance

    def __getitem__(self, k, default=Undefined):
        v = getattr(self.instance, k, default)
        if v is Undefined:
            raise KeyError(k)
        return v

    def __setitem__(self, k, v):
        setattr(self.instance, k, v)

    def __delitem__(self, k):
        delattr(self.instance, k)

    def discard(self, k):
        if hasattr(self.instance, k):
            del self[k]

    def pop(self, k):
        if hasattr(self.instance, k):
            del self[k]
    
    set = __setitem__
    get = __getitem__
