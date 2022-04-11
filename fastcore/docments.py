# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/06_docments.ipynb (unless otherwise specified).


from __future__ import annotations


__all__ = ['docstring', 'parse_docstring', 'empty', 'docments']

# Cell
#nbdev_comment from __future__ import annotations

import re
from tokenize import tokenize,COMMENT
from ast import parse,FunctionDef
from io import BytesIO
from textwrap import dedent
from types import SimpleNamespace
from inspect import getsource,isfunction,isclass,signature,Parameter
from .utils import *

from fastcore import docscrape
from inspect import isclass,getdoc

# Cell
def docstring(sym):
    "Get docstring for `sym` for functions ad classes"
    if isinstance(sym, str): return sym
    res = getdoc(sym)
    if not res and isclass(sym): res = getdoc(sym.__init__)
    return res or ""

# Cell
def parse_docstring(sym):
    "Parse a numpy-style docstring in `sym`"
    docs = docstring(sym)
    return AttrDict(**docscrape.NumpyDocString(docstring(sym)))

# Cell
def _parses(s):
    "Parse Python code in string or function object `s`"
    return parse(dedent(getsource(s) if isfunction(s) else s))

def _tokens(s):
    "Tokenize Python code in string or function object `s`"
    if isfunction(s): s = getsource(s)
    return tokenize(BytesIO(s.encode('utf-8')).readline)

_clean_re = re.compile('^\s*#(.*)\s*$')
def _clean_comment(s):
    res = _clean_re.findall(s)
    return res[0] if res else None

def _param_locs(s, returns=True):
    "`dict` of parameter line numbers to names"
    body = _parses(s).body
    if len(body)!=1 or not isinstance(body[0], FunctionDef): return None
    defn = body[0]
    res = {arg.lineno:arg.arg for arg in defn.args.args}
    if returns and defn.returns: res[defn.returns.lineno] = 'return'
    return res

# Cell
empty = Parameter.empty

# Cell
def _get_comment(line, arg, comments, parms):
    if line in comments: return comments[line].strip()
    line -= 1
    res = []
    while line and line in comments and line not in parms:
        res.append(comments[line])
        line -= 1
    return dedent('\n'.join(reversed(res))) if res else None

def _get_full(anno, name, default, docs):
    if anno==empty and default!=empty: anno = type(default)
    return AttrDict(docment=docs.get(name), anno=anno, default=default)

# Cell
def _merge_doc(dm, npdoc):
    if not npdoc: return dm
    if not dm.anno or dm.anno==empty: dm.anno = npdoc.type
    if not dm.docment: dm.docment = '\n'.join(npdoc.desc)
    return dm

def _merge_docs(dms, npdocs):
    npparams = npdocs['Parameters']
    params = {nm:_merge_doc(dm,npparams.get(nm,None)) for nm,dm in dms.items()}
    if 'return' in dms: params['return'] = _merge_doc(dms['return'], npdocs['Returns'])
    return params

# Cell
def docments(s, full=False, returns=True, eval_str=False):
    "`dict` of parameter names to 'docment-style' comments in function or string `s`"
    nps = parse_docstring(s)
    if isclass(s): s = s.__init__ # Constructor for a class
    comments = {o.start[0]:_clean_comment(o.string) for o in _tokens(s) if o.type==COMMENT}
    parms = _param_locs(s, returns=returns)
    docs = {arg:_get_comment(line, arg, comments, parms) for line,arg in parms.items()}

    if isinstance(s,str): s = eval(s)
    sig = signature(s)
    res = {arg:_get_full(p.annotation, p.name, p.default, docs) for arg,p in sig.parameters.items()}
    if returns: res['return'] = _get_full(sig.return_annotation, 'return', empty, docs)
    res = _merge_docs(res, nps)
    if eval_str:
        hints = type_hints(s)
        for k,v in res.items():
            if k in hints: v['anno'] = hints.get(k)
    if not full: res = {k:v['docment'] for k,v in res.items()}
    return AttrDict(res)