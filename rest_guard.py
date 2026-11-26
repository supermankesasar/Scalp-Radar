"""Shared REST throttle on explicit Binance rate limits; no bypass."""
import threading,time
class RestGuard:
    def __init__(self):self.lock=threading.Lock();self.until=0.
    def pause(self,headers=None):
        try:delay=float((headers or {}).get('Retry-After','300'))
        except (ValueError,TypeError):delay=300.
        with self.lock:self.until=max(self.until,time.monotonic()+max(300.,delay))
    def remaining(self):
        with self.lock:return max(0.,self.until-time.monotonic())
    def check(self):
        if self.remaining()>0:raise RuntimeError('Binance rate limit cooldown active')
REST_GUARD=RestGuard()
