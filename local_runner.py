"""Windows/local launcher: stable DB, crash recovery, prevent idle sleep while running."""
import ctypes,os,sqlite3,subprocess,sys,time,tempfile
from auto_update import check_update,apply_update,output
from pathlib import Path
from database_location import configured,canonical
ROOT=Path(__file__).resolve().parent

def stable_db():
    custom=configured()
    if custom is not None:
        if not custom.is_file():raise RuntimeError('Configured database missing; refusing to create an empty database: '+str(custom))
        return custom
    old=ROOT/'data'/'signals.sqlite3'
    dest=canonical();root=dest.parent
    root.mkdir(parents=True,exist_ok=True)
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

UPDATE_INTERVAL=60
RESTART_UPDATED=86
def monitor(child,request,live):
    """Never apply code while the old child is alive. No forced update kill."""
    while True:
        try:return child.wait(timeout=UPDATE_INTERVAL if live else None),None
        except subprocess.TimeoutExpired:pass
        try:old,target=check_update()
        except (OSError,RuntimeError,subprocess.TimeoutExpired) as exc:
            print('Live update check skipped:',exc,flush=True);continue
        if old==target:continue
        if child.poll() is not None:return child.returncode,None
        print('New GitHub version',target[:12],'- requesting graceful scanner shutdown',flush=True)
        request.write_text(target,encoding='utf-8')
        # Wait for active scan and worker transactions to finish. A slow drain
        # must never trigger a forced kill just to install an update.
        while True:
            try:code=child.wait(timeout=30);break
            except subprocess.TimeoutExpired:print('Update pending: scanner still draining; source unchanged.',flush=True)
        if code!=0:
            print('Scanner did not exit cleanly; postponing update.',flush=True)
            return code,None
        return code,(old,target)

def main():
    env=dict(os.environ);env['SCANNER_DB']=str(stable_db())
    print('Persistent database:',env['SCANNER_DB'],flush=True)
    live=env.get('SCANNER_LIVE_UPDATE')=='1'
    if live:print('Live GitHub update enabled: every 60 seconds; graceful restart only.',flush=True)
    if sys.platform=='win32':ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    delay=10;child=None
    try:
        while True:
            started=time.monotonic()
            with tempfile.TemporaryDirectory(prefix='scalp-radar-stop-') as control:
                request=Path(control)/'shutdown.request'
                env['SCANNER_SHUTDOWN_FILE']=str(request)
                child=subprocess.Popen([sys.executable,'-u',str(ROOT/'app.py')],cwd=ROOT,env=env)
                try:code,pending=monitor(child,request,live)
                except KeyboardInterrupt:
                    if child.poll() is None:
                        request.write_text('manual stop',encoding='utf-8')
                        child.wait()
                    return 0
                child=None
            if pending:
                old,target=pending
                try:
                    apply_update(old,target)
                except (OSError,RuntimeError,subprocess.TimeoutExpired) as exc:
                    print('Update failed:',exc,flush=True)
                    # Restart previous code only if it is still intact.
                    if output('rev-parse','HEAD')!=old or output('status','--porcelain','--untracked-files=no'):
                        print('Checkout no longer clean at previous version; manual recovery required.',flush=True)
                        return 1
                    print('Restarting previous version; next update check in 60 seconds.',flush=True)
                    env['SCANNER_OPEN_BROWSER']='0'
                    continue
                return RESTART_UPDATED
            if code==0:return 0
            env['SCANNER_OPEN_BROWSER']='0'
            if time.monotonic()-started>300:delay=10
            print('Scanner exited with',code,'; retry in',delay,'seconds (Ctrl+C to stop).',flush=True)
            time.sleep(delay);delay=min(120,delay*2)
    except KeyboardInterrupt:
        return 0
    finally:
        if sys.platform=='win32':ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
if __name__=='__main__':sys.exit(main())
