from .remote_pdb import RemotePdb

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Debugger:
    __metaclass__ = Singleton
    def __init__(self):
        self._remote_pdb = RemotePdb('127.0.0.1', 4444) # 444 is my port, you can use another one if you prefer.

    def set_trace(self):
        self._remote_pdb.set_trace()
