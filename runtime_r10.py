"""Local worker supervision and persistent operational heartbeat."""
import json,os,time,threading
from pathlib import Path
class Runtime:
    def __init__(self,path):
        self.path=Path(path).parent/'r10-heartbeat.json'
        self.log=self.path.with_name('r10-runtime.jsonl')
        self.stop=threading.Event();self.lock=threading.RLock();self.workers={}
        self.started=time.time()
        try:
            prior=json.loads(self.path.read_text())
            self.event('previous_heartbeat',gapSeconds=max(0,self.started-prior['time']))
        except (OSError,ValueError,KeyError):pass
    def event(self,event,**details):
        with self.lock:
            with self.log.open('a',encoding='utf-8') as f:f.write(json.dumps(dict(time=time.time(),event=event,**details))+'\n')
    def beat(self,name,**details):
        with self.lock:self.workers.setdefault(name,{}).update(time=time.time(),**details)
    def supervise(self,name,fn):
        def loop():
            while not self.stop.is_set():
                self.beat(name,state='running')
                try:fn()
                except Exception as e:self.event('worker_error',worker=name,error=str(e)[:300])
                if self.stop.is_set():break
                self.beat(name,state='restarting');self.event('worker_restart',worker=name)
                self.stop.wait(10)
        threading.Thread(target=loop,daemon=True,name=name).start()
    def status(self):
        with self.lock:return {'time':time.time(),'started':self.started,'workers':{k:dict(v) for k,v in self.workers.items()}}
    def watch(self,scan_status):
        while not self.stop.wait(30):
            now=time.time();status=self.status();scan=scan_status()
            status['scan']=scan
            try:
                tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps(status),encoding='utf-8');os.replace(tmp,self.path)
            except OSError as e:print('R10 heartbeat:',e,flush=True)
            stalled=[k for k,v in status['workers'].items() if k in ('scan-scheduler','ws-research') and now-v['time']>600]
            if scan.get('running') and scan.get('progressAt') and now-scan['progressAt']/1000>900:stalled.append('scan-job')
            if stalled:
                self.event('watchdog_restart',workers=stalled)
                print('R10 watchdog restart:',stalled,flush=True);os._exit(75)
