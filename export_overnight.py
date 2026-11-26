"""Consistent SQLite backup and compressed export, safe while server is running."""
import os,sqlite3,zipfile,tempfile
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
canonical=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local'/'share')))/'ScalpRadar'/'data'/'signals.sqlite3'
source=Path(os.getenv('SCANNER_DB',str(canonical if canonical.exists() else ROOT/'data'/'signals.sqlite3'))).resolve()
if not source.is_file(): raise SystemExit('Database not found: '+str(source))
out=ROOT/'exports'
out.mkdir(exist_ok=True)
dest=out/('scalp-radar-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.zip')
with tempfile.TemporaryDirectory() as d:
    snapshot=Path(d)/'signals.sqlite3'
    src=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True,timeout=30)
    dst=sqlite3.connect(snapshot)
    try: src.backup(dst,pages=500,sleep=.1)
    finally: dst.close();src.close()
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.write(snapshot,'signals.sqlite3')
        for name in ('r10-heartbeat.json','r10-runtime.jsonl'):
            p=source.parent/name
            if p.is_file():z.write(p,name)
print('EXPORT OK:',dest)
