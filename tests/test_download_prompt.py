from app.agent import SYSTEM_PROMPT


def download_policy():
    return SYSTEM_PROMPT.split('DOWNLOAD WORKFLOW --', 1)[1].split('Identify the intended outcome', 1)[0]


def test_download_policy_separates_generation_menu_transfer_and_artifact():
    policy = download_policy()
    stages = [policy.index(text) for text in (
        '1. If the user requests a generated file',
        '2. Inspect the completed result',
        '3. Choose the transfer tool',
        '4. Interpret the tool result',
        '5. Verify the artifact',
        '6. Report generation and download independently',
    )]
    assert stages == sorted(stages)
    assert 'A menu opener is not the file-download control' in policy
    assert 'never arm a native download against a menu opener' in policy


def test_download_policy_polls_same_attempt_before_task_cleanup():
    policy = download_policy()
    assert 'wait_for_download(download_id)' in policy
    assert 'observe the SAME attempt again' in policy
    assert 'Never re-click, re-arm or generate again' in policy
    assert 'task cleanup\ncloses the browser and cancels pending transfers' in policy
    assert 'it does not replace wait_for_download' in policy


def test_download_policy_requires_verified_output_and_private_source_urls():
    policy = download_policy()
    assert 'status=ready with an artifact' in policy
    assert 'purpose=output' in policy
    assert 'list_task_files (this tool lists READY files only)' in policy
    assert 'artifacts[].download_url' in policy
    assert 'do not copy signed URLs into arguments' in policy
    assert 'never invent a URL or substitute the project page' in policy
    assert 'never execute software, extract archives' in policy


def test_download_policy_does_not_invent_site_specific_capabilities():
    policy = download_policy()
    assert 'Do not assume\nright-click, context-menu, sleep, or OS file-dialog tools exist' in policy
    assert 'Never use browser Save As/keyboard shortcuts' in policy
    assert 'Google Flow' not in policy
