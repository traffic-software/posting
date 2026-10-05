import base64
import struct
import zlib
import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import ToolMessage
from langchain_core.tools import ToolException
from langchain_openai.chat_models.base import _convert_message_to_dict

from app.visual_targets import VisualTargets, _STATE, _MASK, _UNMASK, _HIT
from app.task_context import TaskContext
from app.desktop_tools import DesktopTools


def fixture():
    def chunk(kind, data):
        return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data))
    png = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',100,80,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+b'\0'*300)*80))+chunk(b'IEND',b'')
    state = dict(document='doc',revision=0,url='https://example.com',x=0,y=0,width=100,height=80,
                 screenX=0,screenY=0,outerWidth=108,outerHeight=170,dpr=1,focused=True)
    events=[]
    class Driver:
        current_window_handle='window'
        def execute_script(self,script,*args):
            if script==_STATE:return dict(state)
            if script==_MASK:events.append('mask');return True
            if script==_UNMASK:events.append('unmask');return None
            if script==_HIT:return object()
        def execute_cdp_cmd(self,*args):return {'data':base64.b64encode(png).decode()}
    desktop=SimpleNamespace(_activate_page=lambda:None, _guard=lambda:None, click_viewport=lambda *args:events.append('click'))
    context=TaskContext()
    clock=[0]
    visual=VisualTargets(Driver(),desktop,context,clock=lambda:clock[0])
    return visual,state,events,clock,context


def test_real_image_blocks_reach_adapter_without_text_stringification():
    visual,_,events,_,context=fixture()
    blocks=visual.capture(lambda:None)
    translated=_convert_message_to_dict(ToolMessage(content=blocks,tool_call_id='capture'))
    assert translated['role']=='tool'
    assert translated['content'][1]['type']=='image_url'
    assert translated['content'][1]['image_url']['url'].startswith('data:image/png;base64,')
    assert events==['mask','unmask']
    assert 'data:image' not in context.redact(str(blocks))
    assert context.redact(blocks[1]['image_url']['url'].split(',',1)[1]) == '[IMAGE OMITTED]'
    metadata=json.loads(blocks[0]['text'])
    visual.click(metadata['screenshot_id'],20,30,lambda:None)
    assert events[-1]=='click'
    with pytest.raises(ToolException):visual.click(metadata['screenshot_id'],20,30,lambda:None)


@pytest.mark.parametrize('key,value',[('url','https://other.example'),('document','new'),('revision',1),('x',5),('height',90),('screenX',1),('dpr',2)])
def test_changed_geometry_document_mutation_rejects_click(key,value):
    visual,state,events,_,_=fixture()
    token=json.loads(visual.capture(lambda:None)[0]['text'])['screenshot_id']
    state[key]=value
    with pytest.raises(ToolException):visual.click(token,1,1,lambda:None)
    assert 'click' not in events and visual.current is None


@pytest.mark.parametrize('x,y',[(True,1),(float('nan'),1),(1,float('inf')),(-1,1),(100,1),(1,80)])
def test_invalid_coordinate_consumes_token_without_click(x,y):
    visual,_,events,_,_=fixture()
    token=json.loads(visual.capture(lambda:None)[0]['text'])['screenshot_id']
    with pytest.raises(ToolException):visual.click(token,x,y,lambda:None)
    assert 'click' not in events and visual.current is None


def test_expiry_epoch_unknown_and_forbidden_hit():
    visual,_,events,clock,context=fixture()
    token=json.loads(visual.capture(lambda:None)[0]['text'])['screenshot_id']
    clock[0]=16
    with pytest.raises(ToolException):visual.click(token,1,1,lambda:None)
    clock[0]=0
    token=json.loads(visual.capture(lambda:None)[0]['text'])['screenshot_id']
    context.control.epoch+=1
    with pytest.raises(ToolException):visual.click(token,1,1,lambda:None)
    token=json.loads(visual.capture(lambda:None)[0]['text'])['screenshot_id']
    original=visual.driver.execute_script
    visual.driver.execute_script=lambda script,*args:None if script==_HIT else original(script,*args)
    with pytest.raises(ToolException):visual.click(token,1,1,lambda:None)
    assert 'click' not in events


def test_mask_restored_on_capture_failure_and_size_limits():
    visual,state,events,_,_=fixture()
    visual.driver.execute_cdp_cmd=lambda *args: {'data':'invalid'}
    with pytest.raises(ToolException):visual.capture(lambda:None)
    assert events==['mask','unmask'] and visual.current is None
    state['width']=2000
    with pytest.raises(ToolException):visual.capture(lambda:None)


def test_common_content_to_physical_mapping_and_dpr_rejection():
    raw=dict(x=20,y=30,screenX=10,screenY=10,outerWidth=108,outerHeight=170,
             innerWidth=100,innerHeight=80,screenWidth=1024,screenHeight=768,dpr=1)
    point=DesktopTools._map_point(raw)
    assert (point.x,point.y)==(34,130)
    raw['dpr']=2
    with pytest.raises(ValueError):DesktopTools._map_point(raw)


def test_tool_opt_in_permissions_and_observations_never_store_image(monkeypatch):
    import time
    from app.config import Settings
    from app.selenium_tools import browser_tools
    from app import selenium_tools
    visual,_,_,_,context=fixture()
    driver=visual.driver
    driver.current_url='https://example.com'
    driver.find_element=lambda *args:SimpleNamespace(text='Synthetic canvas')
    monkeypatch.setattr(selenium_tools,'check_url',lambda _:None)
    monkeypatch.setattr('app.visual_targets.VisualTargets',lambda *args:visual)
    settings=Settings(_env_file=None,enable_browser_vision=True)
    tools={t.name:t for t in browser_tools(driver,settings,time.monotonic()+60,context,desktop=visual.desktop)}
    assert 'capture_browser_screenshot' in tools and 'click_screenshot_coordinate' not in tools
    response=tools['capture_browser_screenshot'].invoke({})
    assert response[1]['type']=='image_url'
    message=tools['capture_browser_screenshot'].invoke({'type':'tool_call','name':'capture_browser_screenshot','args':{},'id':'visual-call'})
    assert isinstance(message,ToolMessage)
    assert _convert_message_to_dict(message)['content'][1]['type']=='image_url'
    assert 'base64' not in str(context.observations())
    context.allow_write_actions=True
    settings.enable_write_actions=True
    tools={t.name:t for t in browser_tools(driver,settings,time.monotonic()+60,context,desktop=visual.desktop)}
    assert 'click_screenshot_coordinate' in tools
    with pytest.raises(Exception):
        tools['click_screenshot_coordinate'].invoke({'screenshot_id':'id','x':True,'y':1})
    settings.enable_browser_vision=False
    assert not any('screenshot' in t.name for t in browser_tools(driver,settings,time.monotonic()+60,context,desktop=visual.desktop))


def test_provider_rejection_invalidates_images_and_reports_safe_capability():
    from app.agent import ControlMiddleware
    visual,_,_,_,context=fixture()
    context._visual_targets=visual
    blocks=visual.capture(lambda:None)
    request=SimpleNamespace(messages=[ToolMessage(content=blocks,tool_call_id='x')])
    def reject(request):raise ValueError('private provider details')
    with pytest.raises(RuntimeError,match='capability'):
        ControlMiddleware(context).wrap_model_call(request,reject)
    assert visual.disabled and visual.current is None
    assert 'private provider' not in str(context.observations())
