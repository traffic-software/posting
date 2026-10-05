"""In-memory masked viewport images and conservative one-use visual targets."""
import base64
import struct
import json
import math
import secrets
import time

from langchain_core.tools import ToolException

_STATE = """
if (window !== window.top || document.querySelector('iframe,frame') ||
    Array.from(document.querySelectorAll('*')).some(el=>el.shadowRoot || el.localName.includes('-'))) throw Error('unsupported frame/shadow region');
if (!window.__postingVisual) {
 const state = {id: Array.from(crypto.getRandomValues(new Uint32Array(4))).join('-'), revision: 0};
 new MutationObserver(() => state.revision++).observe(document, {subtree:true,childList:true,attributes:true,characterData:true});
 window.__postingVisual = state;
}
if (document.getAnimations().some(a => a.playState === 'running')) throw Error('active animation');
const canvases=Array.from(document.querySelectorAll('canvas')).map(c=>{
 if(c.width*c.height>2304000) throw Error('canvas too large');
 const ctx=c.getContext('2d'); if(!ctx) throw Error('unsupported canvas');
 const pixels=ctx.getImageData(0,0,c.width,c.height).data;
 let hash=2166136261; for(const byte of pixels) hash=Math.imul(hash^byte,16777619);
 return [c.width,c.height,hash];
});
return {canvases,document:window.__postingVisual.id, revision:window.__postingVisual.revision,
 url:location.href, x:scrollX,y:scrollY,width:innerWidth,height:innerHeight,
 screenX,screenY,outerWidth,outerHeight,dpr:devicePixelRatio,focused:document.hasFocus()};
"""
_MASK = """
if (document.querySelector('iframe,frame')) throw Error('unsupported frame');
const overlays=[];
const nodes=document.querySelectorAll('input,textarea,select,[contenteditable], [data-private], [data-sensitive], [autocomplete="one-time-code"]');
try {
 for (const el of nodes) {
  const r=el.getBoundingClientRect(); if (!r.width || !r.height) continue;
  if (!Number.isFinite(r.x+r.y+r.width+r.height)) throw Error('invalid mask');
  const mask=document.createElement('div');
  mask.style.cssText=`position:fixed!important;left:${r.left}px!important;top:${r.top}px!important;width:${r.width}px!important;height:${r.height}px!important;background:#101820!important;opacity:1!important;z-index:2147483647!important;pointer-events:auto!important;transform:none!important;`;
  document.documentElement.appendChild(mask); overlays.push(mask);
  const hit=document.elementFromPoint(Math.max(0,Math.min(innerWidth-1,r.left+r.width/2)),Math.max(0,Math.min(innerHeight-1,r.top+r.height/2)));
  if (r.right>0 && r.bottom>0 && r.left<innerWidth && r.top<innerHeight && hit!==mask) throw Error('mask obscured');
 }
 window.__postingMasks=overlays;
 return true;
} catch(e) { overlays.forEach(el=>el.remove()); throw e; }
"""
_UNMASK = "(window.__postingMasks || []).forEach(el=>el.remove()); delete window.__postingMasks;"
_HIT = """
const x=arguments[0],y=arguments[1];
const el=document.elementFromPoint(x,y);
if (!el || !document.hasFocus() || window!==window.top) return null;
for(let p=el;p;p=p.parentElement) {
 if (p.matches('iframe,frame,input,textarea,select,[contenteditable],label,[data-private],[data-sensitive]')) return null;
 if (p.matches(':disabled,[aria-disabled="true"]')) return null;
}
return el;
"""


class VisualTargets:
    def __init__(self, driver, desktop, context=None, *, clock=time.monotonic):
        self.driver, self.desktop, self.context = driver, desktop, context
        self.clock = clock
        self.current = None
        self.disabled = False

    def invalidate(self):
        self.current = None

    def _state(self):
        try:
            state = self.driver.execute_script(_STATE)
            if not isinstance(state, dict) or state.get('dpr') != 1 or not state.get('focused'):
                raise ValueError()
            state['window'] = self.driver.current_window_handle
            state['epoch'] = self.context.control.epoch if self.context else 0
            return state
        except Exception:
            self.invalidate()
            raise ToolException('Visual capture requires a stable focused DPR=1 viewport without frames or animations') from None

    def capture(self, guard):
        self.invalidate()
        if self.disabled:
            raise ToolException('Configured model rejected image input; visual tools are unavailable for this task')
        guard()
        self.desktop._activate_page()
        before = self._state()
        if not (0 < before['width'] <= 1920 and 0 < before['height'] <= 1200):
            raise ToolException('Visual viewport exceeds supported dimensions')
        masked = False
        try:
            masked = self.driver.execute_script(_MASK) is True
            if not masked:
                raise ValueError()
            guard()
            masked_state = self._state()
            response = self.driver.execute_cdp_cmd('Page.captureScreenshot', {
                'format':'png', 'fromSurface':True, 'captureBeyondViewport':False,
                'clip':{'x':before['x'],'y':before['y'],'width':before['width'],'height':before['height'],'scale':1},
            })
            if self._state() != masked_state:
                raise ValueError()
            if not isinstance(response.get('data'), str) or len(response['data']) > 2_700_000:
                raise ValueError()
            raw = base64.b64decode(response['data'], validate=True)
            if len(raw) > 2_000_000:
                raise ValueError()
            if raw[:8] != b'\x89PNG\r\n\x1a\n' or raw[12:16] != b'IHDR':
                raise ValueError()
            width, height = struct.unpack('!II', raw[16:24])
            if (width, height) != (before['width'], before['height']):
                raise ValueError()
        except Exception:
            raise ToolException('Could not establish a safely masked bounded viewport image') from None
        finally:
            try:
                self.driver.execute_script(_UNMASK)
            except Exception:
                self.disabled = True
                raise ToolException('Screenshot masking cleanup failed; visual tools disabled') from None
        guard()
        after = self._state()
        if any(before[key] != after[key] for key in before if key != 'revision'):
            raise ToolException('Browser changed during capture; capture again')
        token = secrets.token_urlsafe(24)
        self.current = {'id':token,'at':self.clock(),'state':after,'width':width,'height':height}
        if self.context:
            self.context._vision_payload = base64.b64encode(raw).decode('ascii')
        return [{'type':'text','text':json.dumps({'screenshot_id':token,'width':width,'height':height,
                 'coordinates':'image pixels; origin top-left of browser content viewport','expires_seconds':15})},
                {'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(raw).decode('ascii')}}]

    def click(self, screenshot_id, x, y, guard):
        record, self.current = self.current, None  # consume BEFORE any attempted action
        if not record or screenshot_id != record['id'] or self.clock()-record['at'] > 15:
            raise ToolException('Screenshot target is unknown, consumed or expired; capture again')
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (x,y)):
            raise ToolException('Screenshot coordinates must be finite numeric image pixels')
        if not (0 <= x < record['width'] and 0 <= y < record['height']):
            raise ToolException('Screenshot coordinates must be inside the content image')
        guard()
        self.desktop._activate_page()
        if self._state() != record['state']:
            raise ToolException('Screenshot browser/document/viewport changed; capture again')
        element = self.driver.execute_script(_HIT,x,y)
        if element is None:
            raise ToolException('Visual target is secret, file, frame, disabled or unsupported')
        self.desktop.click_viewport(x,y,record['state'],lambda:self._state()==record['state'],guard)
        return 'One viewport click dispatched; observe the outcome before any further action'
