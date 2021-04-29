# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/03_xtras.ipynb (unless otherwise specified).

__all__ = ['dict2obj', 'obj2dict', 'repr_dict', 'is_listy', 'shufflish', 'mapped', 'IterLen', 'ReindexCollection',
           'maybe_open', 'image_size', 'bunzip', 'join_path_file', 'loads', 'loads_multi', 'untar_dir', 'repo_details',
           'run', 'open_file', 'save_pickle', 'load_pickle', 'truncstr', 'spark_chars', 'sparkline', 'autostart',
           'EventTimer', 'stringfmt_names', 'PartialFormatter', 'partial_format', 'utc2local', 'local2utc', 'trace',
           'round_multiple', 'modified_env', 'ContextManagers', 'str2bool', 'sort_by_run']

# Cell
from .imports import *
from .foundation import *
from .basics import *
from functools import wraps

import mimetypes,pickle,random,json,subprocess,shlex,bz2,gzip,zipfile,tarfile
import imghdr,struct,distutils.util,tempfile,time,string,collections
from contextlib import contextmanager,ExitStack
from pdb import set_trace
from datetime import datetime, timezone
from timeit import default_timer

# Cell
def dict2obj(d):
    "Convert (possibly nested) dicts (or lists of dicts) to `AttrDict`"
    if isinstance(d, (L,list)): return L(d).map(dict2obj)
    if not isinstance(d, dict): return d
    return AttrDict(**{k:dict2obj(v) for k,v in d.items()})

# Cell
def obj2dict(d):
    "Convert (possibly nested) AttrDicts (or lists of AttrDicts) to `dict`"
    if isinstance(d, (L,list)): return list(L(d).map(obj2dict))
    if not isinstance(d, dict): return d
    return dict(**{k:obj2dict(v) for k,v in d.items()})

# Cell
def _repr_dict(d, lvl):
    if isinstance(d,dict):
        its = [f"{k}: {_repr_dict(v,lvl+1)}" for k,v in d.items()]
    elif isinstance(d,(list,L)): its = [_repr_dict(o,lvl+1) for o in d]
    else: return str(d)
    return '\n' + '\n'.join([" "*(lvl*2) + "- " + o for o in its])

# Cell
def repr_dict(d):
    "Print nested dicts and lists, such as returned by `dict2obj`"
    return _repr_dict(d,0).strip()

# Cell
@patch
def __repr__(self:AttrDict): return repr_dict(self)

AttrDict._repr_markdown_ = AttrDict.__repr__

# Cell
def is_listy(x):
    "`isinstance(x, (tuple,list,L,slice,Generator))`"
    return isinstance(x, (tuple,list,L,slice,Generator))

# Cell
def shufflish(x, pct=0.04):
    "Randomly relocate items of `x` up to `pct` of `len(x)` from their starting location"
    n = len(x)
    return L(x[i] for i in sorted(range_of(x), key=lambda o: o+n*(1+random.random()*pct)))

# Cell
def mapped(f, it):
    "map `f` over `it`, unless it's not listy, in which case return `f(it)`"
    return L(it).map(f) if is_listy(it) else f(it)

# Cell
#hide
class IterLen:
    "Base class to add iteration to anything supporting `__len__` and `__getitem__`"
    def __iter__(self): return (self[i] for i in range_of(self))

# Cell
@docs
class ReindexCollection(GetAttr, IterLen):
    "Reindexes collection `coll` with indices `idxs` and optional LRU cache of size `cache`"
    _default='coll'
    def __init__(self, coll, idxs=None, cache=None, tfm=noop):
        if idxs is None: idxs = L.range(coll)
        store_attr()
        if cache is not None: self._get = functools.lru_cache(maxsize=cache)(self._get)

    def _get(self, i): return self.tfm(self.coll[i])
    def __getitem__(self, i): return self._get(self.idxs[i])
    def __len__(self): return len(self.coll)
    def reindex(self, idxs): self.idxs = idxs
    def shuffle(self): random.shuffle(self.idxs)
    def cache_clear(self): self._get.cache_clear()
    def __getstate__(self): return {'coll': self.coll, 'idxs': self.idxs, 'cache': self.cache, 'tfm': self.tfm}
    def __setstate__(self, s): self.coll,self.idxs,self.cache,self.tfm = s['coll'],s['idxs'],s['cache'],s['tfm']

    _docs = dict(reindex="Replace `self.idxs` with idxs",
                shuffle="Randomly shuffle indices",
                cache_clear="Clear LRU cache")

# Cell
@contextmanager
def maybe_open(f, mode='r', **kwargs):
    "Context manager: open `f` if it is a path (and close on exit)"
    if isinstance(f, (str,os.PathLike)):
        with open(f, mode, **kwargs) as f: yield f
    else: yield f

# Cell
def image_size(fn):
    "Tuple of (w,h) for png, gif, or jpg; `None` otherwise"
    d = dict(png=_png_size, gif=_gif_size, jpeg=_jpg_size)
    with maybe_open(fn, 'rb') as f: return d[imghdr.what(f)](f)

# Cell
def bunzip(fn):
    "bunzip `fn`, raising exception if output already exists"
    fn = Path(fn)
    assert fn.exists(), f"{fn} doesn't exist"
    out_fn = fn.with_suffix('')
    assert not out_fn.exists(), f"{out_fn} already exists"
    with bz2.BZ2File(fn, 'rb') as src, out_fn.open('wb') as dst:
        for d in iter(lambda: src.read(1024*1024), b''): dst.write(d)

# Cell
def join_path_file(file, path, ext=''):
    "Return `path/file` if file is a string or a `Path`, file otherwise"
    if not isinstance(file, (str, Path)): return file
    path.mkdir(parents=True, exist_ok=True)
    return path/f'{file}{ext}'

# Cell
def loads(s, cls=None, object_hook=None, parse_float=None,
          parse_int=None, parse_constant=None, object_pairs_hook=None, **kw):
    "Same as `json.loads`, but handles `None`"
    if not s: return {}
    return json.loads(s, cls=cls, object_hook=object_hook, parse_float=parse_float,
          parse_int=parse_int, parse_constant=parse_constant, object_pairs_hook=object_pairs_hook, **kw)

# Cell
def loads_multi(s:str):
    "Generator of >=0 decoded json dicts, possibly with non-json ignored text at start and end"
    _dec = json.JSONDecoder()
    while s.find('{')>=0:
        s = s[s.find('{'):]
        obj,pos = _dec.raw_decode(s)
        if not pos: raise ValueError(f'no JSON object found at {pos}')
        yield obj
        s = s[pos:]

# Cell
def untar_dir(file, dest):
    with tempfile.TemporaryDirectory(dir='.') as d:
        d = Path(d)
        with tarfile.open(mode='r:gz', fileobj=file) as t: t.extractall(d)
        next(d.iterdir()).rename(dest)

# Cell
def repo_details(url):
    "Tuple of `owner,name` from ssh or https git repo `url`"
    res = remove_suffix(url.strip(), '.git')
    res = res.split(':')[-1]
    return res.split('/')[-2:]

# Cell
def run(cmd, *rest, same_in_win=False, ignore_ex=False, as_bytes=False, stderr=False):
    "Pass `cmd` (splitting with `shlex` if string) to `subprocess.run`; return `stdout`; raise `IOError` if fails"
    # Even the command is same on Windows, we have to add `cmd /c `"
    import logging
    if rest:
        if sys.platform == 'win32' and same_in_win:
            cmd = ('cmd', '/c', cmd, *rest)
        else:
            cmd = (cmd,)+rest
    elif isinstance(cmd, str):
        if sys.platform == 'win32' and same_in_win: cmd = 'cmd /c ' + cmd
        cmd = shlex.split(cmd)
    elif isinstance(cmd, list):
        if sys.platform == 'win32' and same_in_win: cmd = ['cmd', '/c'] + cmd
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = res.stdout
    if stderr and res.stderr: stdout += b' ;; ' + res.stderr
    if not as_bytes: stdout = stdout.decode().strip()
    if ignore_ex: return (res.returncode, stdout)
    if res.returncode: raise IOError(stdout)
    return stdout

# Cell
def open_file(fn, mode='r', **kwargs):
    "Open a file, with optional compression if gz or bz2 suffix"
    if isinstance(fn, io.IOBase): return fn
    fn = Path(fn)
    if   fn.suffix=='.bz2': return bz2.BZ2File(fn, mode, **kwargs)
    elif fn.suffix=='.gz' : return gzip.GzipFile(fn, mode, **kwargs)
    elif fn.suffix=='.zip': return zipfile.ZipFile(fn, mode, **kwargs)
    else: return open(fn,mode, **kwargs)

# Cell
def save_pickle(fn, o):
    "Save a pickle file, to a file name or opened file"
    with open_file(fn, 'wb') as f: pickle.dump(o, f)

# Cell
def load_pickle(fn):
    "Load a pickle file from a file name or opened file"
    with open_file(fn, 'rb') as f: return pickle.load(f)

# Cell
@patch
def readlines(self:Path, hint=-1, encoding='utf8'):
    "Read the content of `self`"
    with self.open(encoding=encoding) as f: return f.readlines(hint)

# Cell
@patch
def read_json(self:Path, encoding=None, errors=None):
    "Same as `read_text` followed by `loads`"
    return loads(self.read_text(encoding=encoding, errors=errors))

# Cell
@patch
def mk_write(self:Path, data, encoding=None, errors=None, mode=511):
    "Make all parent dirs of `self`, and write `data`"
    self.parent.mkdir(exist_ok=True, parents=True, mode=mode)
    self.write_text(data, encoding=encoding, errors=errors)

# Cell
@patch
def ls(self:Path, n_max=None, file_type=None, file_exts=None):
    "Contents of path as a list"
    extns=L(file_exts)
    if file_type: extns += L(k for k,v in mimetypes.types_map.items() if v.startswith(file_type+'/'))
    has_extns = len(extns)==0
    res = (o for o in self.iterdir() if has_extns or o.suffix in extns)
    if n_max is not None: res = itertools.islice(res, n_max)
    return L(res)

# Cell
@patch
def __repr__(self:Path):
    b = getattr(Path, 'BASE_PATH', None)
    if b:
        try: self = self.relative_to(b)
        except: pass
    return f"Path({self.as_posix()!r})"

# Cell
def truncstr(s:str, maxlen:int, suf:str='…', space='')->str:
    "Truncate `s` to length `maxlen`, adding suffix `suf` if truncated"
    return s[:maxlen-len(suf)]+suf if len(s)+len(space)>maxlen else s+space

# Cell
spark_chars = '▁▂▃▅▆▇'

# Cell
def _ceil(x, lim=None): return x if (not lim or x <= lim) else lim

def _sparkchar(x, mn, mx, incr, empty_zero):
    if x is None or (empty_zero and not x): return ' '
    if incr == 0: return spark_chars[0]
    res = int((_ceil(x,mx)-mn)/incr-0.5)
    return spark_chars[res]

# Cell
def sparkline(data, mn=None, mx=None, empty_zero=False):
    "Sparkline for `data`, with `None`s (and zero, if `empty_zero`) shown as empty column"
    valid = [o for o in data if o is not None]
    if not valid: return ' '
    mn,mx,n = ifnone(mn,min(valid)),ifnone(mx,max(valid)),len(spark_chars)
    res = [_sparkchar(x=o, mn=mn, mx=mx, incr=(mx-mn)/n, empty_zero=empty_zero) for o in data]
    return ''.join(res)

# Cell
def autostart(g):
    "Decorator that automatically starts a generator"
    @functools.wraps(g)
    def f():
        r = g()
        next(r)
        return r
    return f

# Cell
class EventTimer:
    "An event timer with history of `store` items of time `span`"
    def __init__(self, store=5, span=60):
        self.hist,self.span,self.last = collections.deque(maxlen=store),span,default_timer()
        self._reset()

    def _reset(self): self.start,self.events = self.last,0

    def add(self, n=1):
        "Record `n` events"
        if self.duration>self.span:
            self.hist.append(self.freq)
            self._reset()
        self.events +=n
        self.last = default_timer()

    @property
    def duration(self): return default_timer()-self.start
    @property
    def freq(self): return self.events/self.duration

# Cell
_fmt = string.Formatter()

# Cell
def stringfmt_names(s:str)->list:
    "Unique brace-delimited names in `s`"
    return uniqueify(o[1] for o in _fmt.parse(s) if o[1])

# Cell
class PartialFormatter(string.Formatter):
    "A `string.Formatter` that doesn't error on missing fields, and tracks missing fields and unused args"
    def __init__(self):
        self.missing = set()
        super().__init__()

    def get_field(self, nm, args, kwargs):
        try: return super().get_field(nm, args, kwargs)
        except KeyError:
            self.missing.add(nm)
            return '{'+nm+'}',nm

    def check_unused_args(self, used, args, kwargs):
        self.xtra = filter_keys(kwargs, lambda o: o not in used)

# Cell
def partial_format(s:str, **kwargs):
    "string format `s`, ignoring missing field errors, returning missing and extra fields"
    fmt = PartialFormatter()
    res = fmt.format(s, **kwargs)
    return res,list(fmt.missing),fmt.xtra

# Cell
def utc2local(dt:datetime)->datetime:
    "Convert `dt` from UTC to local time"
    return dt.replace(tzinfo=timezone.utc).astimezone(tz=None)

# Cell
def local2utc(dt:datetime)->datetime:
    "Convert `dt` from local to UTC time"
    return dt.replace(tzinfo=None).astimezone(tz=timezone.utc)

# Cell
def trace(f):
    "Add `set_trace` to an existing function `f`"
    if getattr(f, '_traced', False): return f
    def _inner(*args,**kwargs):
        set_trace()
        return f(*args,**kwargs)
    _inner._traced = True
    return _inner

# Cell
def round_multiple(x, mult, round_down=False):
    "Round `x` to nearest multiple of `mult`"
    def _f(x_): return (int if round_down else round)(x_/mult)*mult
    res = L(x).map(_f)
    return res if is_listy(x) else res[0]

# Cell
@contextmanager
def modified_env(*delete, **replace):
    "Context manager temporarily modifying `os.environ` by deleting `delete` and replacing `replace`"
    prev = dict(os.environ)
    try:
        os.environ.update(replace)
        for k in delete: os.environ.pop(k, None)
        yield
    finally:
        os.environ.clear()
        os.environ.update(prev)

# Cell
class ContextManagers(GetAttr):
    "Wrapper for `contextlib.ExitStack` which enters a collection of context managers"
    def __init__(self, mgrs): self.default,self.stack = L(mgrs),ExitStack()
    def __enter__(self): self.default.map(self.stack.enter_context)
    def __exit__(self, *args, **kwargs): self.stack.__exit__(*args, **kwargs)

# Cell
def str2bool(s):
    "Case-insensitive convert string `s` too a bool (`y`,`yes`,`t`,`true`,`on`,`1`->`True`)"
    if not isinstance(s,str): return bool(s)
    return bool(distutils.util.strtobool(s)) if s else False

# Cell
def _is_instance(f, gs):
    tst = [g if type(g) in [type, 'function'] else g.__class__ for g in gs]
    for g in tst:
        if isinstance(f, g) or f==g: return True
    return False

def _is_first(f, gs):
    for o in L(getattr(f, 'run_after', None)):
        if _is_instance(o, gs): return False
    for g in gs:
        if _is_instance(f, L(getattr(g, 'run_before', None))): return False
    return True

# Cell
def sort_by_run(fs):
    end = L(fs).attrgot('toward_end')
    inp,res = L(fs)[~end] + L(fs)[end], L()
    while len(inp):
        for i,o in enumerate(inp):
            if _is_first(o, inp):
                res.append(inp.pop(i))
                break
        else: raise Exception("Impossible to sort")
    return res