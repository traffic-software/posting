"""In-memory masked viewport images and conservative one-use visual targets."""
import base64
import struct
import json
import math
import secrets
import time
import sys

from concurrent.futures import CancelledError

from langchain_core.tools import ToolException

from app.task_context import TaskControlError

_STATE = """
try {
if (window !== window.top || document.querySelector('iframe,frame')) return {guard:'state_frame'};
const elements=Array.from(document.querySelectorAll('*'));
if (elements.some(el=>el.shadowRoot)) return {guard:'state_shadow_root'};
if (elements.some(el=>el.localName.includes('-'))) return {guard:'state_custom_element'};
if (!window.__postingVisual) {
 const state = {id: Array.from(crypto.getRandomValues(new Uint32Array(4))).join('-'), revision: 0};
 new MutationObserver(() => state.revision++).observe(document, {subtree:true,childList:true,attributes:true,characterData:true});
 window.__postingVisual = state;
}
if (document.getAnimations().some(a => a.playState === 'running')) return {guard:'state_animation'};
const canvases=[];
for (const c of document.querySelectorAll('canvas')) {
 if(c.width*c.height>2304000) return {guard:'state_canvas_large'};
 const ctx=c.getContext('2d'); if(!ctx) return {guard:'state_canvas_context'};
 let pixels;
 try { pixels=ctx.getImageData(0,0,c.width,c.height).data; }
 catch(e) { return {guard:'state_canvas_pixels'}; }
 let hash=2166136261; for(const byte of pixels) hash=Math.imul(hash^byte,16777619);
 canvases.push([c.width,c.height,hash]);
}
return {canvases,document:window.__postingVisual.id, revision:window.__postingVisual.revision,
 url:location.href, x:scrollX,y:scrollY,width:innerWidth,height:innerHeight,
 screenX,screenY,outerWidth,outerHeight,dpr:devicePixelRatio,focused:document.hasFocus()};
} catch(e) { return {guard:'state_script'}; }
"""
# Ordinary content mode checks geometry, not unrelated animation/canvas pixels.
_PAGE_STATE = """
try {
 if (window !== window.top) return {guard:'state_frame'};
 const elements=Array.from(document.querySelectorAll('*'));
 if (elements.some(el=>el.shadowRoot)) return {guard:'state_shadow_root'};
 if (elements.some(el=>el.localName.includes('-'))) return {guard:'state_custom_element'};
 if (!window.__postingVisual) {
  const state={id:Array.from(crypto.getRandomValues(new Uint32Array(4))).join('-'),revision:0};
  new MutationObserver(()=>state.revision++).observe(document,{subtree:true,childList:true,attributes:true,characterData:true});
  window.__postingVisual=state;
 }
 return {document:window.__postingVisual.id,revision:window.__postingVisual.revision,
  url:location.href,x:scrollX,y:scrollY,width:innerWidth,height:innerHeight,
  screenX,screenY,outerWidth,outerHeight,dpr:devicePixelRatio,focused:document.hasFocus()};
} catch(e) { return {guard:'state_script'}; }
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
_PAGE_MASK = _MASK.replace("if (document.querySelector('iframe,frame')) throw Error('unsupported frame');", "").replace(
    'input,textarea,select,[contenteditable], [data-private], [data-sensitive], [autocomplete="one-time-code"]',
    'iframe,frame,input[type="password"],input[type="hidden"],[autocomplete="username"],[autocomplete="current-password"],[autocomplete="new-password"],[autocomplete="one-time-code"],[data-private],[data-sensitive]'
)
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


VISUAL_GUARD_MESSAGES = {
    'disabled': 'Configured model rejected image input; visual tools are unavailable for this task',
    'state_driver': 'Visual capture state check failed at the browser service',
    'state_invalid': 'Visual capture received an invalid viewport state',
    'state_dpr': 'Visual capture requires devicePixelRatio=1; the current DPR is unsupported',
    'state_focus': 'Visual capture requires a focused browser document',
    'state_frame': 'Visual capture is unavailable for a frame context or a page containing frames',
    'state_shadow_root': 'Visual capture is unavailable for a page containing shadow DOM',
    'state_custom_element': 'Visual capture is unavailable for a page containing custom elements',
    'state_animation': 'Visual capture is unavailable while CSS or Web Animations are running',
    'state_canvas_large': 'Visual capture encountered a canvas exceeding the supported size',
    'state_canvas_context': 'Visual capture encountered an unsupported canvas context',
    'state_canvas_pixels': 'Visual capture could not safely read canvas pixels',
    'state_script': 'Visual capture could not validate the page state',
    'dimensions': 'Visual viewport exceeds supported dimensions',
    'mask': 'Could not establish a safely masked bounded viewport image: masking failed',
    'screenshot': 'Could not establish a safely masked bounded viewport image: screenshot capture failed',
    'image': 'Could not establish a safely masked bounded viewport image: image validation failed',
    'state_changed': 'Could not establish a safely masked bounded viewport image: page state changed',
    'cleanup': 'Screenshot masking cleanup failed; visual tools disabled',
    'browser_changed': 'Browser changed during capture; capture again',
}


class VisualGuardError(ToolException):
    def __init__(self, code):
        self.diagnostic_code = code if code in VISUAL_GUARD_MESSAGES else 'state_invalid'
        super().__init__(VISUAL_GUARD_MESSAGES[self.diagnostic_code])


class VisualTargets:
    def __init__(self, driver, desktop, context=None, *, clock=time.monotonic):
        self.driver, self.desktop, self.context = driver, desktop, context
        self.clock = clock
        self.current = None
        self.disabled = False

    def invalidate(self):
        self.current = None

    def _state(self, page_content=False):
        try:
            state = self.driver.execute_script(_PAGE_STATE if page_content else _STATE)
            if not isinstance(state, dict):
                raise VisualGuardError('state_invalid')
            if 'guard' in state:
                code = state['guard']
                raise VisualGuardError(code if isinstance(code, str) else 'state_invalid')
            if state.get('dpr') != 1:
                raise VisualGuardError('state_dpr')
            if not state.get('focused'):
                raise VisualGuardError('state_focus')
            state['window'] = self.driver.current_window_handle
            state['epoch'] = self.context.control.epoch if self.context else 0
            return state
        except VisualGuardError:
            self.invalidate()
            raise
        except (TimeoutError, TaskControlError, CancelledError):
            self.invalidate()
            raise
        except Exception:
            self.invalidate()
            raise VisualGuardError('state_driver') from None

    def capture(self, guard, *, page_content=False):
        self.invalidate()
        if self.disabled:
            raise VisualGuardError('disabled')
        guard()
        self.desktop._activate_page()
        before = self._state(page_content)
        if not (0 < before['width'] <= 1920 and 0 < before['height'] <= 1200):
            raise VisualGuardError('dimensions')
        masked = False
        failure_code = 'mask'
        try:
            masked = self.driver.execute_script(_PAGE_MASK if page_content else _MASK) is True
            if not masked:
                raise ValueError()
            guard()
            masked_state = self._state(page_content)
            failure_code = 'screenshot'
            response = self.driver.execute_cdp_cmd('Page.captureScreenshot', {
                'format':'png', 'fromSurface':True, 'captureBeyondViewport':False,
                'clip':{'x':before['x'],'y':before['y'],'width':before['width'],'height':before['height'],'scale':1},
            })
            captured_state = self._state(page_content)
            if captured_state != masked_state:
                raise VisualGuardError('state_changed')
            failure_code = 'image'
            if not isinstance(response, dict) or not isinstance(response.get('data'), str) or len(response['data']) > 2_700_000:
                raise ValueError()
            raw = base64.b64decode(response['data'], validate=True)
            if len(raw) > 2_000_000:
                raise ValueError()
            if raw[:8] != b'\x89PNG\r\n\x1a\n' or raw[12:16] != b'IHDR':
                raise ValueError()
            width, height = struct.unpack('!II', raw[16:24])
            if (width, height) != (before['width'], before['height']):
                raise ValueError()
        except (VisualGuardError, TimeoutError, TaskControlError, CancelledError):
            raise
        except Exception:
            raise VisualGuardError(failure_code) from None
        finally:
            primary_failure = sys.exc_info()[0] is not None
            try:
                self.driver.execute_script(_UNMASK)
            except Exception:
                self.disabled = True
                if not primary_failure:
                    raise VisualGuardError('cleanup') from None
                # Cleanup must not overwrite the exception that stopped execution.
                if self.context:
                    self.context.record_observation('visual_cleanup', 'stopped', VISUAL_GUARD_MESSAGES['cleanup'], code='cleanup')
        guard()
        after = self._state(page_content)
        if any(before[key] != after[key] for key in before if key != 'revision'):
            raise VisualGuardError('browser_changed')
        token = secrets.token_urlsafe(24)
        self.current = {'id':token,'at':self.clock(),'state':after,'width':width,'height':height,'page_content':page_content}
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
        page_content = record.get('page_content', False)
        def same_state():
            current = self._state(page_content)
            return all(current[key] == record['state'][key] for key in record['state'] if not page_content or key != 'revision')
        if not same_state():
            raise ToolException('Screenshot browser/document/viewport changed; capture again')
        element = self.driver.execute_script(_HIT,x,y)
        if element is None:
            raise ToolException('Visual target is secret, file, frame, disabled or unsupported')
        bounds_script = "const el=arguments[0]; for(let p=el;p;p=p.parentElement){if(p.getAnimations().some(a=>a.playState==='running'))return null;} const r=el.getBoundingClientRect();return [r.x,r.y,r.width,r.height];"
        bounds = self.driver.execute_script(bounds_script, element) if page_content else None
        if page_content and (not isinstance(bounds, list) or len(bounds) != 4):
            raise ToolException('Visual target is moving or unsupported; capture again')
        def fresh():
            if not same_state():
                return False
            if page_content:
                return self.driver.execute_script(_HIT,x,y) == element and self.driver.execute_script(bounds_script, element) == bounds
            return True
        self.desktop.click_viewport(x,y,record['state'],fresh,guard)
        return 'One viewport click dispatched; observe the outcome before any further action'
