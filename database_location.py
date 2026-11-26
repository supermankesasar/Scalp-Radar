"""Persistent local database location shared by launcher, export and migration."""
import json,os
from pathlib import Path

def app_home():
    return Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local'/'share')))/'ScalpRadar'

def config_path():
    return app_home()/'database-location.json'

def canonical():
    return app_home()/'data'/'signals.sqlite3'

def configured():
    override=os.environ.get('SCANNER_DB')
    if override:
        return Path(override).resolve()
    cfg=config_path()
    if not cfg.exists():return None
    try:
        p=Path(json.loads(cfg.read_text(encoding='utf-8'))['database'])
        if not p.is_absolute():raise ValueError('database path must be absolute')
        return p
    except (OSError,ValueError,KeyError,TypeError) as e:
        raise RuntimeError('Invalid saved database location; refusing fallback: '+str(cfg)) from e

def existing_database(root):
    selected=configured()
    if selected is not None:
        if not selected.is_file():raise RuntimeError('Configured database missing; reconnect drive or correct location: '+str(selected))
        return selected
    default=canonical()
    if default.is_file():return default
    old=Path(root)/'data'/'signals.sqlite3'
    if old.is_file():return old
    raise RuntimeError('No existing Scalp Radar database found')

def save_location(path):
    path=Path(path).resolve()
    if not path.is_file():raise RuntimeError('Cannot select missing database')
    cfg=config_path()
    cfg.parent.mkdir(parents=True,exist_ok=True)
    temp=cfg.with_suffix('.tmp')
    try:
        temp.write_text(json.dumps({'database':str(path)},indent=2),encoding='utf-8')
        os.replace(temp,cfg)
    finally:
        if temp.exists():temp.unlink()
