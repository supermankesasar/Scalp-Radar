"""Windows/local launcher: stable DB, crash recovery, prevent idle sleep while running."""
import ctypes,os,sqlite3,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def stable_db():
    custom=os.environ.get('SCANNER_DB')
    if custom:return Path(custom).resolve()
    old=ROOT/'data'/'signals.sqlite3'
    root=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local'/'share')))/'ScalpRadar'/'data'
    root.mkdir(parents=True,exist_ok=True);dest=root/'signals.sqlite3'
    if old.is_file() and not dest.exists():
        temp=root/'migration.sqlite3.tmp'
        if temp.exists():temp.unlink()
        src=sqlite3.connect(old.resolve().as_uri()+'?mode=ro',uri=True);dst=sqlite3.connect(temp)
        try:
            src.backup(dst)
            if dst.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise RuntimeError('Database migration integrity check failed')
        finally:dst.close();src.close()
        # Never overwrite an existing canonical database.
        if dest.exists():raise RuntimeError('Canonical database appeared during migration')
        temp.rename(dest);print('Copied existing DB; original retained:',old,flush=True)
    elif old.is_file() and dest.exists():
        print('Canonical DB already exists; old folder DB NOT merged:',old,flush=True)
    elif not dest.exists():
        print('No old DB found in this folder. To keep prior research, restore/copy it before first launch.',flush=True)
        if os.environ.get('SCANNER_ALLOW_NEW_DB')!='1':
            if input('Create a NEW empty database? Type YES to confirm: ').strip()!='YES':raise SystemExit('Cancelled; no database created.')
    return dest

def main():
    env=dict(os.environ);env['SCANNER_DB']=str(stable_db())
    print('Persistent database:',env['SCANNER_DB'],flush=True)
    if sys.platform=='win32':ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    delay=10;child=None
    try:
        while True:
            started=time.monotonic()
            child=subprocess.Popen([sys.executable,'-u',str(ROOT/'app.py')],cwd=ROOT,env=env)
            code=child.wait();child=None
            if code==0:return 0
            env['SCANNER_OPEN_BROWSER']='0'
            if time.monotonic()-started>300:delay=10
            print('Scanner exited with',code,'; retry in',delay,'seconds (Ctrl+C to stop).',flush=True)
            time.sleep(delay);delay=min(120,delay*2)
    except KeyboardInterrupt:
        if child is not None and child.poll() is None:
            child.terminate();child.wait()
        return 0
    finally:
        if sys.platform=='win32':ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
if __name__=='__main__':sys.exit(main())
