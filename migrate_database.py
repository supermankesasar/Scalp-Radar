"""One-time local, offline SQLite database migration. Original retained."""
import os,shutil,socket,sqlite3,sys,tempfile
from pathlib import Path
from database_location import existing_database,save_location,configured
ROOT=Path(__file__).resolve().parent

def port_active():
    with socket.socket() as sock:
        sock.settimeout(.5)
        return sock.connect_ex(('127.0.0.1',8765))==0

def migrate(source,dest):
    source=Path(source).resolve();dest=Path(dest).resolve()
    if not source.is_file():raise RuntimeError('Source database missing: '+str(source))
    if source==dest:
        save_location(dest)
        return
    if dest.exists():raise RuntimeError('Destination already exists; refusing to overwrite: '+str(dest))
    if not Path(dest.anchor).is_dir():raise RuntimeError('Destination drive unavailable: '+dest.anchor)
    dest.parent.mkdir(parents=True,exist_ok=True)
    estimate=source.stat().st_size
    wal=source.with_name(source.name+'-wal')
    if wal.exists():estimate+=wal.stat().st_size
    if shutil.disk_usage(dest.parent).free<estimate+64*1024*1024:
        raise RuntimeError('Insufficient destination disk space')
    fd,name=tempfile.mkstemp(prefix='migration-',suffix='.sqlite3.tmp',dir=dest.parent)
    os.close(fd);temp=Path(name)
    try:
        src=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True,timeout=10)
        try:
            dst=sqlite3.connect(temp)
            try:
                src.backup(dst,pages=500,sleep=.1)
                if dst.execute('PRAGMA quick_check').fetchone()[0]!='ok':
                    raise RuntimeError('SQLite quick_check failed')
            finally:dst.close()
        finally:src.close()
        # Windows rename refuses existing destinations. On POSIX link is atomic/no-clobber.
        if os.name=='nt':temp.rename(dest)
        else:os.link(temp,dest)
        for name in ('r10-heartbeat.json','r10-runtime.jsonl'):
            old=source.parent/name;new=dest.parent/name
            if old.is_file() and not new.exists():shutil.copy2(old,new)
        save_location(dest)
    finally:
        if temp.exists():temp.unlink()

def main():
    if os.environ.get('SCANNER_DB'):
        raise RuntimeError('SCANNER_DB override is set; clear it before one-click migration to avoid conflicting paths.')
    if port_active():raise RuntimeError('Stop Scalp Radar (including launcher) before migration.')
    source=existing_database(ROOT)
    dest=Path(sys.argv[1]) if len(sys.argv)>1 else Path(r'D:\ScalpRadar\data\signals.sqlite3')
    if not dest.is_absolute():raise RuntimeError('Destination must be an absolute path')
    print('Source:',source,flush=True)
    print('Destination:',dest,flush=True)
    print('Close all scanner/launcher windows. Original database will be retained.',flush=True)
    if input('Type YES to copy and switch database: ').strip()!='YES':return
    if port_active():raise RuntimeError('Scanner is still running; migration cancelled.')
    migrate(source,dest)
    print('Migration OK. Active database:',dest,flush=True)
    print('Original retained. Start START-WINDOWS.bat and verify the displayed database path.',flush=True)

if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError,sqlite3.Error) as exc:
        print('Migration stopped:',exc,flush=True)
        sys.exit(1)
