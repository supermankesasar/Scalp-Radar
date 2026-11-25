"""Import existing research batches into one local SQLite file without mixing run identities.
Run from repository root: python research/import_history.py data/signals.sqlite3
Original immutable JSON files remain untouched; this is a derived indexed archive.
"""
import json
import sys
import threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research_history import ResearchHistory

def main():
    path=Path(sys.argv[1] if len(sys.argv)>1 else ROOT/'data'/'signals.sqlite3')
    path.parent.mkdir(parents=True,exist_ok=True)
    ledger=ResearchHistory(path,threading.RLock())
    files=sorted((ROOT/'research'/'results').glob('*.json'))
    with ledger.connection() as db:
        for p in files:
            d=json.loads(p.read_text(encoding='utf-8'))
            if not isinstance(d,dict) or not isinstance(d.get('records'),list):
                continue
            run='R06-2026-11-24' if p.name.startswith('r06_C') else 'TECH-2026-11-24'
            for r in d['records']:
                direction=r.get('dir',r.get('sg'))
                if direction not in (1,-1):
                    raise ValueError('Invalid direction in '+p.name)
                db.execute('INSERT OR IGNORE INTO research_archive VALUES(?,?,?,?,?,?)',
                    (run,p.stem,r['symbol'],int(r['t']),'UP' if direction==1 else 'DOWN',
                     json.dumps(r,separators=(',',':'),allow_nan=False)))
    print(ledger.summary()['archiveRows'],'archived candidate snapshots')

if __name__=='__main__':
    main()
