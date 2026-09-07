"""Process-local job deduplication; workers never call Streamlit APIs."""
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import tempfile
from pathlib import Path

_lock=threading.RLock()
_jobs={}

def status(key):
    with _lock:return dict(_jobs.get(str(key),{}))

def start(key,fn,cooldown=30):
    key=str(key)
    with _lock:
        prev=_jobs.get(key,{})
        if prev.get('running') or time.monotonic()-prev.get('finished',-1e9)<cooldown:return False
        _jobs[key]={'running':True,'error':None,'started':time.monotonic()}
    def worker():
        error=None
        try:fn()
        except Exception as exc:error=f'{type(exc).__name__}: {exc}'
        finally:
            with _lock:_jobs[key].update(running=False,error=error,finished=time.monotonic())
    threading.Thread(target=worker,daemon=True,name='market-loader').start()
    return True

def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=path.name,suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,allow_nan=False)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def parallel_map(items,fetch,on_result,max_workers=4):
    errors={}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures={pool.submit(fetch,item):key for key,item in items.items()}
        for f in as_completed(futures):
            key=futures[f]
            try:on_result(key,f.result())
            except Exception as exc:errors[key]=str(exc)
    return errors
