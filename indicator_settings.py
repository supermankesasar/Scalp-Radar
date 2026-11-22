"""Persistent, auditable indicator thresholds. Never contains trading credentials."""
import json, math, sqlite3, threading, time
from pathlib import Path

DB_PATH=Path(__file__).resolve().parent/'data'/'indicator_settings.sqlite3'
LOCK=threading.RLock()
DEFAULTS={
    'rsi_watch_threshold':70.0,
    'rsi_long_max':70.0,
    'min_score':68.0,
    'volume_full_score_min':1.10,
    'max_chase_pct':0.30,
}
BOUNDS={
    'rsi_watch_threshold':(50,95),
    'rsi_long_max':(47,90),
    'min_score':(50,95),
    'volume_full_score_min':(0.85,5),
    'max_chase_pct':(0.05,2),
}

def validate(payload):
    if not isinstance(payload,dict) or set(payload)!=set(DEFAULTS):
        raise ValueError('Data harus memuat tepat lima parameter yang tersedia.')
    clean={}
    for k,(lo,hi) in BOUNDS.items():
        v=payload[k]
        if isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or not lo<=v<=hi:
            raise ValueError(f'{k}: gunakan angka antara {lo} dan {hi}.')
        clean[k]=float(v)
    return clean

def _init(db):
    db.execute('''CREATE TABLE IF NOT EXISTS config(
        id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL,
        revision INTEGER NOT NULL, updated_ms INTEGER NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS history(
        revision INTEGER PRIMARY KEY, payload TEXT NOT NULL, updated_ms INTEGER NOT NULL)''')
    db.execute('INSERT OR IGNORE INTO config(id,payload,revision,updated_ms) VALUES(1,?,0,0)',
              (json.dumps(DEFAULTS,sort_keys=True),))

def current():
    with LOCK:
        DB_PATH.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(DB_PATH,timeout=15) as db:
            _init(db)
            payload,revision,updated=db.execute('SELECT payload,revision,updated_ms FROM config WHERE id=1').fetchone()
            return {'values':validate(json.loads(payload)), 'revision':revision, 'updated_ms':updated,
                    'defaults':dict(DEFAULTS), 'bounds':dict(BOUNDS)}

def save(payload):
    values=validate(payload)
    with LOCK:
        DB_PATH.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(DB_PATH,timeout=15) as db:
            _init(db)
            previous=db.execute('SELECT revision,payload FROM config WHERE id=1').fetchone()
            if values==validate(json.loads(previous[1])):
                return current()
            revision=previous[0]+1
            stamp=int(time.time()*1000)
            serialized=json.dumps(values,sort_keys=True)
            db.execute('UPDATE config SET payload=?,revision=?,updated_ms=? WHERE id=1',
                       (serialized,revision,stamp))
            db.execute('INSERT INTO history VALUES(?,?,?)',(revision,serialized,stamp))
        return current()
