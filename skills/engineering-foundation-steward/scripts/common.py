"""Bounded local JSON reads. No network, project commands, or writes."""
import json
import os
from pathlib import Path

LIMIT = 262144

def read_json(path):
    p = Path(path).absolute()
    if any(x.is_symlink() for x in [p, *p.parents]):
        raise ValueError('symlink input refused')
    fd = os.open(str(p), os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'rb') as stream:
        import stat
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('regular file required')
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('input size limit')
    return json.loads(raw)

def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))
