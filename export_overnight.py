"""Consistent SQLite backup and compressed export, safe while server is running."""
import os,sqlite3,zipfile,tempfile
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
source=Path(os.getenv('SCANNER_DB',str(ROOT/'data'/'signals.sqlite3'))).resolve()
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
print('EXPORT OK:',dest)
