"""Synthetic normal-mode fixture only; does not certify retained user UC mode."""
import json
import os
import time
from urllib.parse import quote

import pytest
from langchain_core.messages import ToolMessage
from langchain_openai.chat_models.base import _convert_message_to_dict
from selenium.webdriver.common.by import By

from app.browser_runtime import local_browser
from app.config import Settings
from app.task_context import TaskContext
from app.visual_targets import VisualTargets

pytestmark=pytest.mark.skipif(os.environ.get('RUN_LOCAL_BROWSER_INTEGRATION')!='1',reason='Linux synthetic visual integration opt-in required')


def test_masked_content_image_mock_adapter_canvas_physical_click_and_stale_target(monkeypatch):
    import seleniumbase
    original=seleniumbase.Driver
    def normal_fixture(**kwargs):
        kwargs.update(uc=False,undetectable=False,uc_subprocess=False)
        return original(**kwargs)
    monkeypatch.setattr(seleniumbase,'Driver',normal_fixture)
    settings=Settings(_env_file=None)
    context=TaskContext()
    html='''<html><body style="margin:0"><canvas id="canvas" width="300" height="180"></canvas>
    <input id="secret" type="password" value="synthetic-only">
    <p id="result">Waiting</p><div style="height:1500px"></div><script>
    const c=document.getElementById('canvas');const ctx=c.getContext('2d');
    ctx.fillStyle='blue';ctx.fillRect(20,20,100,80);
    c.onclick=e=>{if(e.offsetX>=20&&e.offsetX<120&&e.offsetY>=20&&e.offsetY<100)document.getElementById('result').textContent='Clicked';};
    </script></body></html>'''
    with local_browser(settings,context,time.monotonic()+60) as session:
        session.driver.get('data:text/html,'+quote(html))
        visual=VisualTargets(session.driver,session.desktop,context)
        blocks=visual.capture(lambda:None)
        translated=_convert_message_to_dict(ToolMessage(content=blocks,tool_call_id='visual'))
        assert translated['content'][1]['type']=='image_url'
        assert session.driver.find_element(By.ID,'secret').get_attribute('value')=='synthetic-only'
        assert session.driver.execute_script('return window.__postingMasks === undefined')
        metadata=json.loads(blocks[0]['text'])
        # Mocked vision selects known pixels in the blue canvas control.
        visual.click(metadata['screenshot_id'],60,60,lambda:None)
        assert session.driver.find_element(By.ID,'result').text=='Clicked'
        blocks=visual.capture(lambda:None)
        session.driver.execute_script("document.getElementById('result').textContent='Changed'")
        with pytest.raises(Exception,match='changed'):
            visual.click(json.loads(blocks[0]['text'])['screenshot_id'],60,60,lambda:None)
        blocks=visual.capture(lambda:None)
        session.driver.execute_script('window.scrollTo(0,100)')
        with pytest.raises(Exception,match='changed'):
            visual.click(json.loads(blocks[0]['text'])['screenshot_id'],60,60,lambda:None)
        session.driver.execute_script('window.scrollTo(0,0)')
        blocks=visual.capture(lambda:None)
        session.driver.execute_script("document.getElementById('canvas').getContext('2d').fillRect(0,0,20,20)")
        with pytest.raises(Exception,match='changed'):
            visual.click(json.loads(blocks[0]['text'])['screenshot_id'],60,60,lambda:None)
