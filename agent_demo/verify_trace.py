#!/usr/bin/env python3
"""Audit the stored wire evidence; this does not call an agent or an MCP server."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    args = parser.parse_args()
    report = json.loads(args.trace.read_text(encoding='utf-8'))
    events = report['events']
    assert report['completed'] and report['session_delete_status'] == 204
    assert events[0]['response']['result']['protocolVersion'] == '2025-11-25'
    assert events[0]['initialized_notification_status'] == 202
    assert {tool['name'] for tool in events[1]['response']['result']['tools']} == {
        'accord_state', 'accord_propose', 'accord_consent', 'accord_transition'}
    calls = [event for event in events if event['request']['method'] == 'tools/call']
    assert len(calls) == 11 and all(event['http_status'] == 200 for event in calls)
    data = lambda event: event['response']['result']['structuredContent']['data']
    states = [data(event) for event in calls if event['request']['params']['name'] == 'accord_state']
    assert len(states) == 4 and states[0] == states[1]
    assert states[0]['version'] == 0 and states[0]['tasks'] == [] and states[0]['plans'] == {}
    errors = [event for event in calls if event['response']['result']['isError']]
    assert len(errors) == 2
    assert errors[0]['request']['params']['name'] == 'accord_propose'
    assert errors[1]['request']['params']['arguments']['action'] == 'commit'
    assert 'Every resident must approve' in errors[1]['response']['result']['structuredContent']['error']
    committed, restored = states[2:]
    assert committed['version'] == 1 and len(committed['tasks']) == 3
    assert committed['cap'] == 2500
    peak = max(sum(task['watts'] for task in committed['tasks'] if task['start'] <= minute < task['end'])
               for minute in range(180))
    assert peak == 2000 and peak <= committed['cap']
    assert all(task['earliest'] <= task['start'] < task['end'] <= task['latest']
               for task in committed['tasks'])
    assert committed['receipts'][0]['approvals'] == ['Alice', 'Bob']
    assert restored['tasks'] == states[0]['tasks'] and restored['version'] == 2
    commit, undo = restored['receipts']
    assert undo['kind'] == 'undo' and undo['target'] == commit['id']
    assert undo['after_hash'] == commit['before_hash']
    # The recording deliberately excludes transport authorization and session headers.
    text = args.trace.read_text(encoding='utf-8')
    assert 'Authorization' not in text and 'Mcp-Session-Id' not in text
    print(json.dumps({'result': 'PASS', 'artifact_sha256': hashlib.sha256(args.trace.read_bytes()).hexdigest(),
                      'exchanges': len(events), 'tool_calls': len(calls), 'expected_refusals': len(errors),
                      'observed_peak_scheduled_watts': peak, 'ceiling_watts': committed['cap'],
                      'undo_restored_initial_tasks': True,
                      'evidence_scope': 'recorded local synthetic exchanges; no identity, device or Alexa proof'}, indent=2))


if __name__ == '__main__':
    main()
