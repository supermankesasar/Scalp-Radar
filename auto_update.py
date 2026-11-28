"""Safe Git updates, with startup launcher and live supervisor helpers."""
import os
import socket
import subprocess
import sys
from pathlib import Path
from database_location import app_home

ROOT=Path(__file__).resolve().parent
ORIGINS={'https://github.com/supermankesasar/Scalp-Radar.git',
         'https://github.com/supermankesasar/Scalp-Radar',
         'git@github.com:supermankesasar/Scalp-Radar.git',
         'ssh://git@github.com/supermankesasar/Scalp-Radar.git'}

def git(*args,timeout=60):
    env=dict(os.environ,GIT_TERMINAL_PROMPT='0')
    return subprocess.run(['git','-C',str(ROOT),*args],capture_output=True,
                          text=True,encoding='utf-8',errors='replace',timeout=timeout,env=env)

def output(*args):
    result=git(*args)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'Git command failed: '+' '.join(args))
    return result.stdout.strip()

def scanner_running():
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex(('127.0.0.1',8765))==0

def check_update():
    """Fetch metadata only; safe while scanner is running. Return old and target."""
    if not (ROOT/'.git').exists():
        raise RuntimeError('This is a ZIP folder, not a Git clone. Clone into a NEW folder first.')
    if output('rev-parse','--show-toplevel').casefold().replace('\\','/')!=str(ROOT).casefold().replace('\\','/'):
        raise RuntimeError('Unexpected repository root.')
    if output('remote','get-url','origin') not in ORIGINS:
        raise RuntimeError('Unexpected Git origin; refusing update.')
    if output('branch','--show-current')!='main':
        raise RuntimeError('Not on main; refusing to switch branches automatically.')
    if output('status','--porcelain','--untracked-files=no'):
        raise RuntimeError('Local tracked files changed; refusing to overwrite them. Use START-WINDOWS.bat to run locally.')
    old=output('rev-parse','HEAD')
    try:
        result=git('fetch','--no-tags','origin','+refs/heads/main:refs/remotes/origin/main',timeout=90)
    except subprocess.TimeoutExpired:
        print('GitHub check timed out; starting existing version '+old[:12],flush=True)
        return old,old
    if result.returncode:
        print('GitHub update check failed; starting existing version '+old[:12],flush=True)
        print(result.stderr.strip(),flush=True)
        return old,old
    target=output('rev-parse','refs/remotes/origin/main')
    if old==target:
        print('Already up to date: '+old[:12],flush=True)
        return old,old
    if git('merge-base','--is-ancestor',old,target).returncode:
        raise RuntimeError('Local main is ahead or diverged; refusing reset or merge.')
    return old,target

def apply_update(old,target):
    if scanner_running():
        raise RuntimeError('Scanner started during update check. Stop it before updating.')
    if output('rev-parse','HEAD')!=old or output('branch','--show-current')!='main' or output('status','--porcelain','--untracked-files=no'):
        raise RuntimeError('Checkout changed during update; refusing merge.')
    if old==target:return old
    if git('merge-base','--is-ancestor',old,target).returncode:
        raise RuntimeError('Target is not a fast-forward.')
    # Never overwrite untracked/ignored files, even if upstream starts tracking them.
    result=git('merge','--ff-only','--no-overwrite-ignore',target)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'Fast-forward failed.')
    actual=output('rev-parse','HEAD')
    if actual!=target:
        raise RuntimeError('Unexpected version after update.')
    print('Updated: '+old[:12]+' -> '+actual[:12],flush=True)
    return actual

def update():
    if scanner_running():
        raise RuntimeError('Scanner is running. Stop the existing terminal before updating.')
    old,target=check_update()
    return apply_update(old,target) if old!=target else old

def main():
    if os.name!='nt':
        print('Use the Windows launcher on Windows.',flush=True)
        return 1
    # An OS-held lock prevents two auto-launchers racing. No stale PID lock.
    import msvcrt
    home=app_home();home.mkdir(parents=True,exist_ok=True)
    with (home/'auto-launch.lock').open('a+b') as lock:
        lock.seek(0,2)
        if lock.tell()==0:lock.write(b'0');lock.flush()
        lock.seek(0)
        try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            print('Another auto-launcher is already running.',flush=True)
            return 1
        try:
            update()
            # Run the newly updated normal launcher, with its existing DB selection.
            env=dict(os.environ,SCANNER_LIVE_UPDATE='1')
            while True:
                code=subprocess.call(['cmd.exe','/d','/c','START-WINDOWS.bat'],cwd=ROOT,env=env)
                if code!=86:return code
                env['SCANNER_OPEN_BROWSER']='0'
                print('Restarting updated scanner...',flush=True)
        except (OSError,RuntimeError,subprocess.TimeoutExpired) as exc:
            print('Auto-update stopped: '+str(exc),flush=True)
            return 1
        finally:
            lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)

if __name__=='__main__':sys.exit(main())
