import json
import time
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.tools import ToolException
from langgraph.errors import GraphRecursionError
from openai import APIConnectionError, APITimeoutError, AuthenticationError, RateLimitError

from app import agent
from app.config import Settings
from app.main import create_app
from app.schemas import TaskStatus
from app.storage import TaskStore
from app.task_context import ExecutionBudget, TaskContext, TaskDeadlineExceeded
from app.task_report import TaskExecutionFailure, diagnostic, failure_diagnostics, output_result
from app.visual_targets import VisualGuardError, VISUAL_GUARD_MESSAGES, _STATE, _MASK, _UNMASK
from test_visual_targets import fixture


@pytest.mark.parametrize('exc,code', [
    (TaskDeadlineExceeded('private'), 'task_deadline'),
    (TimeoutError('private'), 'operation_timeout'),
    (GraphRecursionError('private'), 'agent_step_limit'),
    (APITimeoutError(request=httpx.Request('POST', 'https://private.example')), 'model_timeout'),
    (ToolException('private'), 'tool_error'),
    (ValueError('private'), 'unknown_failure'),
])
def test_classification_never_uses_raw_exception(exc, code):
    details = failure_diagnostics(exc)
    assert details['code'] == code
    assert 'private' not in json.dumps(details)


@pytest.mark.parametrize('kind,code,status', [
    (AuthenticationError, 'model_authentication', 401),
    (RateLimitError, 'model_rate_limit', 429),
])
def test_provider_status_failure_categories(kind, code, status):
    request = httpx.Request('POST', 'https://private.example/?token=private')
    exc = kind('private provider message', response=httpx.Response(status, request=request), body={'private': 'private'})
    details = failure_diagnostics(exc)
    assert details['code'] == code
    assert 'private' not in json.dumps(details)


def test_model_connection_and_untyped_model_failure():
    exc = APIConnectionError(request=httpx.Request('POST', 'https://private.example'))
    assert failure_diagnostics(exc)['code'] == 'model_connection'
    context = TaskContext()
    failure = ValueError('private model response')
    context.record_failure(failure, 'model')
    assert failure_diagnostics(failure, context)['code'] == 'model_error'
    assert failure_diagnostics(ValueError('private different error'), context)['code'] == 'unknown_failure'


def test_model_and_tool_timeout_origins_are_distinct():
    context = TaskContext()
    middleware = agent.ControlMiddleware(context)
    failure = TimeoutError('private model content')

    def broken(_):
        raise failure

    with pytest.raises(TimeoutError):
        middleware.wrap_model_call(SimpleNamespace(messages=[]), broken)
    details = failure_diagnostics(failure, context)
    assert (details['phase'], details['code']) == ('model', 'model_timeout')

    later = ValueError('a different private exception')
    assert failure_diagnostics(later, context)['code'] == 'unknown_failure'
    tool_failure = TimeoutError('private tool content')

    def broken_tool(_):
        raise tool_failure

    with pytest.raises(TimeoutError):
        middleware.wrap_tool_call(SimpleNamespace(tool=SimpleNamespace(name='inspect_page')), broken_tool)
    details = failure_diagnostics(tool_failure, context)
    assert (details['phase'], details['code'], details['tool']) == ('tool', 'operation_timeout', 'inspect_page')


def test_cancel_precedence_and_typed_deadline():
    context = TaskContext()
    context.control.budget = ExecutionBudget(-1)
    with pytest.raises(TaskDeadlineExceeded) as error:
        context.check_alive()
    assert failure_diagnostics(error.value, context)['code'] == 'task_deadline'
    context.cancel()
    assert failure_diagnostics(error.value, context)['code'] == 'task_cancelled'


def test_last_blocker_is_not_used_as_failure_cause():
    context = TaskContext()
    context.record_observation('capture_browser_screenshot', 'stopped', 'private raw contents', code='state_animation')
    details = failure_diagnostics(ValueError('private later failure'), context, phase='agent_execution')
    assert details['code'] == 'unknown_failure'
    assert details['last_tool_blocker']['code'] == 'state_animation'
    assert 'private' not in json.dumps(details)
    context.record_observation('inspect_page', 'stopped', 'https://private.example/?token=secret')
    details = failure_diagnostics(ValueError(), context)
    assert details['last_tool_blocker']['code'] == 'tool_stop'
    assert 'private' not in json.dumps(details)


@pytest.mark.parametrize('text', ['বাংলা' * 6000, '"\\n' * 6000], ids=['unicode', 'escaping'])
def test_result_byte_limit_includes_diagnostics(text):
    details = diagnostic('model_timeout', 'model')
    details['last_tool_blocker'] = {'code': 'state_focus', 'tool': 'capture_browser_screenshot', 'message': 'private'}
    report = output_result(text, details)
    assert len(json.dumps(report, ensure_ascii=False).encode()) <= 8000
    assert report['diagnostics']['code'] == 'model_timeout'
    assert 'private' not in json.dumps(report)


def test_diagnostics_normalization_drops_raw_metadata():
    report = output_result('safe', {'code': [], 'phase': {}, 'message': 'secret', 'traceback': 'secret'})
    assert report['diagnostics']['code'] == 'unknown_failure'
    assert 'secret' not in json.dumps(report)


@pytest.mark.parametrize('code', [
    'state_frame', 'state_shadow_root', 'state_custom_element', 'state_animation',
    'state_canvas_large', 'state_canvas_context', 'state_canvas_pixels', 'state_script',
])
def test_visual_script_markers_are_safe_and_issue_no_token(code):
    visual, _, events, _, _ = fixture()
    visual.driver.execute_script = lambda script, *args: {'guard': code} if script == _STATE else None
    with pytest.raises(VisualGuardError) as error:
        visual.capture(lambda: None)
    assert error.value.diagnostic_code == code
    assert str(error.value) == VISUAL_GUARD_MESSAGES[code]
    assert visual.current is None and not events


@pytest.mark.parametrize('key,value,code', [('dpr', 2, 'state_dpr'), ('focused', False, 'state_focus')])
def test_visual_focus_and_scale_diagnostics(key, value, code):
    visual, state, events, _, _ = fixture()
    state[key] = value
    with pytest.raises(VisualGuardError) as error:
        visual.capture(lambda: None)
    assert error.value.diagnostic_code == code
    assert not events and visual.current is None


@pytest.mark.parametrize('state_result,code', [(None, 'state_invalid'), ({'guard': 'private invalid marker'}, 'state_invalid')])
def test_invalid_visual_state_is_safe(state_result, code):
    visual, _, _, _, _ = fixture()
    visual.driver.execute_script = lambda *_: state_result
    with pytest.raises(VisualGuardError) as error:
        visual.capture(lambda: None)
    assert error.value.diagnostic_code == code
    assert 'private' not in str(error.value)
    assert visual.current is None


def test_visual_driver_error_is_safe():
    visual, _, _, _, _ = fixture()

    def unavailable(*_):
        raise ValueError('private browser error')

    visual.driver.execute_script = unavailable
    with pytest.raises(VisualGuardError) as error:
        visual.capture(lambda: None)
    assert error.value.diagnostic_code == 'state_driver'
    assert 'private' not in str(error.value)
    assert visual.current is None


@pytest.mark.parametrize('stage,code', [('mask', 'mask'), ('screenshot', 'screenshot'), ('image', 'image'), ('cleanup', 'cleanup')])
def test_visual_capture_stages_remain_fail_closed(stage, code):
    visual, _, events, _, _ = fixture()
    original = visual.driver.execute_script

    def script(source, *args):
        if (stage == 'mask' and source == _MASK) or (stage == 'cleanup' and source == _UNMASK):
            raise ValueError('private browser data')
        return original(source, *args)

    visual.driver.execute_script = script
    if stage == 'screenshot':
        def unavailable(*_):
            raise ValueError('private screenshot data')
        visual.driver.execute_cdp_cmd = unavailable
    elif stage == 'image':
        visual.driver.execute_cdp_cmd = lambda *_: {'data': 'private invalid image'}
    with pytest.raises(VisualGuardError) as error:
        visual.capture(lambda: None)
    assert error.value.diagnostic_code == code
    assert 'private' not in str(error.value)
    assert visual.current is None and 'click' not in events
    if stage == 'cleanup':
        assert visual.disabled
    else:
        assert 'unmask' in events


def test_visual_deadline_is_not_relabelled_as_capture_error():
    visual, _, events, _, _ = fixture()
    calls = []

    def guard():
        calls.append(True)
        if len(calls) == 2:
            raise TaskDeadlineExceeded('deadline')

    with pytest.raises(TaskDeadlineExceeded):
        visual.capture(guard)
    assert events == ['mask', 'unmask']
    assert visual.current is None


def test_visual_tool_records_specific_blocker(monkeypatch):
    from app import selenium_tools
    visual, state, _, _, context = fixture()
    state['focused'] = False
    visual.driver.current_url = 'https://example.com'
    visual.driver.find_element = lambda *_: SimpleNamespace(text='Synthetic page')
    monkeypatch.setattr(selenium_tools, 'check_url', lambda _: None)
    monkeypatch.setattr('app.visual_targets.VisualTargets', lambda *_: visual)
    tools = {item.name: item for item in selenium_tools.browser_tools(
        visual.driver, Settings(_env_file=None, enable_browser_vision=True),
        time.monotonic() + 60, context, desktop=visual.desktop,
    )}
    response = tools['capture_browser_screenshot'].invoke({})
    report = json.loads(response[0]['text'])
    assert report['status'] == 'visual_unavailable'
    assert report['code'] == 'state_focus'
    assert 'screenshot_id' not in report
    assert visual.current is None
    assert context.observations()[-2]['code'] == 'state_focus'
    original = visual.driver.execute_script
    visual.driver.execute_script = lambda source, *args: [] if source == selenium_tools.DISCOVER_PAGE else original(source, *args)
    assert json.loads(tools['inspect_page'].invoke({}))['text'] == 'Synthetic page'

    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage, ToolMessage

    class Model(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    model = Model(responses=[
        AIMessage(content='', tool_calls=[{'name': 'capture_browser_screenshot', 'args': {}, 'id': 'capture'}]),
        AIMessage(content='', tool_calls=[{'name': 'inspect_page', 'args': {}, 'id': 'dom'}]),
        AIMessage(content='DOM inspection continued without visual capture.'),
    ])
    graph = agent.create_deep_agent(model=model, tools=list(tools.values()), middleware=[agent.ControlMiddleware(context)])
    state = graph.invoke({'messages': [{'role': 'user', 'content': 'Inspect the synthetic page.'}]})
    results = [message for message in state['messages'] if isinstance(message, ToolMessage)]
    assert len(results) == 2
    assert all(message.status != 'error' for message in results)
    assert 'visual_unavailable' in str(results[0].content)
    assert 'Synthetic page' in results[1].content
    assert state['messages'][-1].content == 'DOM inspection continued without visual capture.'


@pytest.mark.parametrize('diagnosis_succeeds', [False, True])
def test_primary_diagnostics_survive_optional_analysis(monkeypatch, diagnosis_succeeds):
    context = TaskContext()
    context.record_observation('capture_browser_screenshot', 'stopped', 'safe', code='state_animation')

    def broken(*_):
        raise GraphRecursionError('private internal detail')

    monkeypatch.setattr(agent, '_execute_task', broken)

    class Model:
        def invoke(self, _):
            if not diagnosis_succeeds:
                raise RuntimeError('private diagnosis failure')
            return SimpleNamespace(content='Could not complete the requested task.')

    monkeypatch.setattr(agent, 'ChatOpenAI', lambda **_: Model())
    settings = Settings(_env_file=None, openai_api_key='test', openai_base_url='https://model.example/v1', model_name='test')
    with pytest.raises(TaskExecutionFailure) as error:
        agent.run_task('Read title', settings, context)
    assert error.value.result['diagnostics']['code'] == 'agent_step_limit'
    assert error.value.result['diagnostics']['last_tool_blocker']['code'] == 'state_animation'
    assert 'private' not in json.dumps(error.value.result)


@pytest.mark.parametrize('structured', [True, False])
def test_worker_failure_diagnostics_survive_task_status(tmp_path, structured):
    settings = Settings(_env_file=None, database_path=tmp_path / 'tasks.db', openai_api_key='test',
                        openai_base_url='https://model.example/v1', model_name='test', task_api_token='test-token')

    def runner(*_):
        if structured:
            raise TaskExecutionFailure(output_result('Failure report', diagnostic('model_timeout', 'model')))
        raise ValueError('private driver/provider data')

    headers = {'Authorization': 'Bearer test-token'}
    with TestClient(create_app(settings, runner=runner)) as client:
        accepted = client.post('/run-task', json={'prompt': 'Synthetic test'}, headers=headers)
        assert accepted.status_code == 202
        task_id = accepted.json()['task_id']
        for _ in range(200):
            response = client.get('/task-status/' + task_id, headers=headers)
            if response.json()['status'] == 'FAILED':
                break
            time.sleep(.01)
        record = response.json()
        assert record['status'] == 'FAILED'
        assert record['error'] == 'Task execution failed'
        assert record['result']['diagnostics']['code'] == ('model_timeout' if structured else 'unknown_failure')
        assert 'private' not in response.text


def test_cleanup_failure_preserves_primary_deadline():
    visual, _, _, _, context = fixture()
    original = visual.driver.execute_script

    def script(source, *args):
        if source == _UNMASK:
            raise ValueError('private cleanup data')
        return original(source, *args)

    visual.driver.execute_script = script
    calls = []

    def guard():
        calls.append(True)
        if len(calls) == 2:
            raise TaskDeadlineExceeded('private deadline data')

    with pytest.raises(TaskDeadlineExceeded) as error:
        visual.capture(guard)
    details = failure_diagnostics(error.value, context)
    assert details['code'] == 'task_deadline'
    assert details['last_tool_blocker']['code'] == 'cleanup'
    assert visual.disabled and visual.current is None
    assert 'private' not in json.dumps(details)


def test_image_model_timeout_preserves_provider_failure_type():
    visual, _, _, _, context = fixture()
    context._visual_targets = visual
    request = SimpleNamespace(messages=[SimpleNamespace(content=[{'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,AA=='}}])])

    def timeout(_):
        raise APITimeoutError(request=httpx.Request('POST', 'https://private.example'))

    with pytest.raises(RuntimeError) as error:
        agent.ControlMiddleware(context).wrap_model_call(request, timeout)
    details = failure_diagnostics(error.value, context)
    assert details['code'] == 'model_timeout'
    assert details['phase'] == 'model'
    assert visual.disabled
    assert 'private' not in json.dumps(details)


@pytest.mark.parametrize('restart,code', [(False, 'application_shutdown'), (True, 'application_restart')])
def test_storage_lifecycle_failure_has_diagnostics(tmp_path, restart, code):
    store = TaskStore(tmp_path / 'tasks.db')
    store.initialize()
    task_id = store.create('Synthetic', 1)
    store.claim_execution()
    if restart:
        store.recover_interrupted()
    else:
        store.cancel_processing(task_id)
    record = store.get(task_id)
    assert record['status'] == TaskStatus.FAILED
    assert record['result']['diagnostics']['code'] == code
