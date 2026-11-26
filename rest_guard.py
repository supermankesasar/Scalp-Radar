"""Shared REST cooldown and conservative header-driven budget telemetry."""
import threading,time
class RestGuard:
    def __init__(self):
        self.lock=threading.Lock();self.until=0.;self.budget_until=0.
        self.limit=None;self.used=None;self.observed_at=None
    def pause(self,headers=None):
        try:delay=float((headers or {}).get('Retry-After','300'))
        except (ValueError,TypeError):delay=300.
        with self.lock:self.until=max(self.until,time.monotonic()+max(300.,delay))
    def observe(self,headers=None,exchange_info=None):
        """Limit from exchangeInfo, never assume fixed Binance IP capacity."""
        with self.lock:
            if isinstance(exchange_info,dict):
                for item in exchange_info.get('rateLimits',[]):
                    if item.get('rateLimitType')=='REQUEST_WEIGHT' and item.get('interval')=='MINUTE' and item.get('intervalNum')==1:
                        try:
                            limit=int(item['limit'])
                            if limit>0:self.limit=limit
                        except (ValueError,TypeError,KeyError):pass
            try:used=int((headers or {}).get('X-MBX-USED-WEIGHT-1M'))
            except (ValueError,TypeError):return
            now=time.time()
            if self.observed_at is not None and int(now//60)==int(self.observed_at//60):
                used=max(used,self.used)
            self.used=used;self.observed_at=now
            # Best-effort headroom, not a hard limiter; other IP clients/in-flight calls may consume weight.
            if self.limit and used>=.8*self.limit:
                self.budget_until=max(self.budget_until,time.monotonic()+62-now%60)
    def remaining(self):
        with self.lock:return max(0.,max(self.until,self.budget_until)-time.monotonic())
    def check(self):
        if self.remaining()>0:raise RuntimeError('Binance rate limit cooldown active')
    def status(self):
        with self.lock:
            return {'weight1m':self.used,'limit1m':self.limit,'observedAt':self.observed_at,
                    'cooldownSeconds':max(0.,max(self.until,self.budget_until)-time.monotonic()),
                    'note':'Header-based best effort; unknown until observed; shared IP usage may change.'}
REST_GUARD=RestGuard()
