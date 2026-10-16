#!/usr/bin/env python3
"""Render an honest, paced visualization of recorded real MCP HTTP exchanges.

This is an execution viewer, not a recording of the product's browser interface.
Recorded responses drive the displayed agenda. The video never fabricates a reply.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
TRACE = json.loads((ROOT / 'recorded_execution.json').read_text())
W, H, FPS = 1280, 720, 12
BG = '#f4f6f9'
INK = '#152638'
MUTED = '#536477'
BLUE = '#2465e8'
GREEN = '#087a5a'
RED = '#b52b35'
LINE = '#dbe2ec'
FONT_DIR = Path('/usr/share/fonts/truetype/dejavu')


def font(size, bold=False, mono=False):
    name = 'DejaVuSansMono.ttf' if mono else ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')
    return ImageFont.truetype(str(FONT_DIR / name), size)


F = {name: font(size, bold, mono) for name, size, bold, mono in [
    ('title', 35, True, False), ('head', 24, True, False), ('body', 21, False, False),
    ('small', 16, False, False), ('tiny', 14, False, False), ('code', 19, False, True),
    ('caption', 24, False, False), ('metric', 35, True, False), ('hero', 50, True, False)
]}

SCENES = [
    {'event': None, 'duration': 6, 'title': 'A shared home. An agreed agenda.',
     'caption': 'Home Accord: three household requests, one shared power limit. Local simulation; no appliances are connected.'},
    {'event': 0, 'duration': 6, 'title': 'Connect to the running MCP server',
     'caption': 'This is a paced replay of a live agent’s decisions, executed again over real local HTTP. No new AI inference occurs in this replay.'},
    {'event': 1, 'duration': 6, 'title': 'Discover the four available tools',
     'caption': 'The client discovers the server’s actual tools before proposing, approving, applying or undoing anything.'},
    {'event': 2, 'duration': 8, 'title': 'Read the current household state',
     'caption': 'The server reports an empty agenda, version zero, and a 2,500-watt ceiling. All times are relative planning minutes.'},
    {'event': 3, 'duration': 10, 'title': 'A tight request meets a real refusal',
     'caption': 'Three independent hour-long tasks cannot be placed in the requested one-hour window by this greedy planner.'},
    {'event': 4, 'duration': 6, 'title': 'Check that refusal changed nothing',
     'caption': 'A separate state read confirms the rejected request created neither tasks nor a saved proposal.'},
    {'event': 5, 'duration': 14, 'title': 'Adapt the request, preserve the limit',
     'caption': 'The recorded agent decision widens the windows to three hours. The server proposes sequential tasks below the unchanged 2,500-watt ceiling.'},
    {'event': 6, 'duration': 10, 'title': 'Missing simulated consent blocks commit',
     'caption': 'A premature commit is refused. Both demo roles must approve this exact proposal before the agenda can change.'},
    {'event': 7, 'duration': 8, 'title': 'Record the first simulated approval',
     'caption': 'Alice is a selectable demo role, not an authenticated person. This explicit simulation records only the first required approval.'},
    {'event': 8, 'duration': 8, 'title': 'Record the second simulated approval',
     'caption': 'Bob’s simulated approval is attached to the same proposal. Both required role approvals are now present.'},
    {'event': 9, 'duration': 12, 'title': 'Apply the exact approved proposal',
     'caption': 'The server returns a commit receipt at version one. We still read the agenda separately to verify the resulting state.'},
    {'event': 10, 'duration': 12, 'title': 'Verify the agenda after the commit',
     'caption': 'Three tasks are now observed in the agenda. Peak scheduled power is 2,000 watts; no physical device operation or energy savings are claimed.'},
    {'event': 11, 'duration': 10, 'title': 'Reverse the latest change',
     'caption': 'Undo returns a reversal receipt at version two. Receipts record local consistency, not human identity or appliance execution.'},
    {'event': 12, 'duration': 12, 'title': 'Read again: the original agenda returns',
     'caption': 'The final read shows an empty task list again. Reversal restored the original agenda while retaining the change history.'},
    {'event': None, 'duration': 10, 'title': 'Propose. Agree. Apply. Undo.',
     'caption': '13 recorded exchanges. 11 tool calls. Two refusals. A verified reversal. Full source, trace and run instructions accompany this demonstration.'},
]
TOTAL = sum(scene['duration'] for scene in SCENES)


def wrapped(draw, text, pos, max_width, style='body', color=INK, spacing=6):
    x, y = pos
    words = text.split()
    line = ''
    for word in words:
        candidate = (line + ' ' + word).strip()
        if line and draw.textlength(candidate, font=F[style]) > max_width:
            draw.text((x, y), line, font=F[style], fill=color)
            y += F[style].size + spacing
            line = word
        else:
            line = candidate
    if line:
        draw.text((x, y), line, font=F[style], fill=color)
        y += F[style].size + spacing
    return y


def badge(draw, x, y, text, color=BLUE, light='#eaf0ff', size='small'):
    width = draw.textlength(text, font=F[size]) + 24
    draw.rounded_rectangle((x, y, x + width, y + 30), radius=9, fill=light)
    draw.text((x + 12, y + 5), text, font=F[size], fill=color)
    return width


def brief_request(event):
    req = event['request']
    if req['method'] == 'initialize':
        return ['initialize', 'protocol: 2025-11-25', 'transport: Streamable HTTP']
    if req['method'] == 'tools/list':
        return ['tools/list', 'arguments: {}']
    params = req['params']
    args = params['arguments']
    lines = [params['name']]
    if params['name'] == 'accord_state':
        return lines + ['arguments: {}']
    if params['name'] == 'accord_propose':
        for task in args['requests']:
            lines.append(f"{task['owner']}: {task['appliance']}")
        task = args['requests'][0]
        return lines + [f"each duration: {task['duration']} min", f"window: {task['earliest']}–{task['latest']} min"]
    if params['name'] == 'accord_consent':
        return lines + [f"resident: {args['resident']}", 'approved: true', 'simulation_acknowledged: true',
                        f"plan: {args['plan_id'][:8]}…"]
    return lines + [f"action: {args['action']}", 'confirmed: true', f"id: {args['id'][:8]}…"]


def brief_response(event):
    result = event['response']['result']
    if event['request']['method'] == 'initialize':
        return ['protocolVersion: ' + result['protocolVersion'], 'server: ' + result['serverInfo']['name'],
                'initialized notification: HTTP 202']
    if event['request']['method'] == 'tools/list':
        return [tool['name'] for tool in result['tools']]
    content = result['structuredContent']
    if result['isError']:
        if 'Every resident' in content['error']:
            return ['isError: true', 'Every resident must approve this exact', 'proposal before committing.']
        return ['isError: true', 'No feasible placement found by the', 'greedy planner. Widen a window.', 'Not proof of global infeasibility.']
    data = content['data']
    name = event['request']['params']['name']
    if name == 'accord_state':
        return [f"version: {data['version']}", f"cap: {data['cap']} W | tasks: {len(data['tasks'])}",
                f"plans: {len(data['plans'])} | receipts: {len(data['receipts'])}"]
    if name in ('accord_propose', 'accord_consent'):
        return [f"plan: {data['id'][:8]}…", f"status: {data['status']}",
                'approvals: ' + (', '.join(data['approvals']) or 'none'), f"tasks proposed: {len(data['additions'])}"]
    return [f"receipt: {data['kind']} | version: {data['version']}",
            f"id: {data['id'][:8]}…", f"after_hash: {data['after_hash'][:14]}…"]


def update_state(previous, event):
    state = deepcopy(previous)
    if event['request']['method'] != 'tools/call':
        return state
    result = event['response']['result']
    name = event['request']['params']['name']
    if result['isError']:
        state['notice'] = 'REFUSED · no agenda change'
        return state
    data = result['structuredContent']['data']
    state['notice'] = ''
    if name == 'accord_state':
        state.update({'known': True, 'version': data['version'], 'cap': data['cap'], 'tasks': data['tasks'],
                      'receipts': len(data['receipts'])})
        if data['tasks']:
            state['mode'] = 'Observed committed agenda'
        elif data['version'] == 2:
            state['mode'] = 'Observed restored agenda'
            state['proposal'] = []
            state['approvals'] = []
            state['notice'] = 'UNDO VERIFIED · original task list restored'
        else:
            state['mode'] = 'Observed empty agenda'
    elif name in ('accord_propose', 'accord_consent'):
        state.update({'proposal': data['additions'], 'approvals': data['approvals'], 'mode': 'Proposed agenda · not yet applied'})
    elif data['kind'] == 'commit':
        state['notice'] = 'Commit receipt received · next: read state'
    elif data['kind'] == 'undo':
        state['notice'] = 'Undo receipt received · next: read state'
    return state


def right_panel(draw, state, progress):
    x, y, width = 665, 153, 575
    draw.rounded_rectangle((x, y, x + width, 580), radius=18, fill='white', outline=LINE, width=1)
    draw.text((x + 24, y + 20), 'HOUSEHOLD STATE', font=F['small'], fill=MUTED)
    if not state['known']:
        wrapped(draw, 'Waiting for the first state read', (x + 24, y + 86), width - 48, 'head')
        wrapped(draw, 'The display is derived from real MCP responses. Nothing here is appliance telemetry.',
                (x + 24, y + 158), width - 56, 'body', MUTED)
        return
    draw.text((x + 24, y + 55), f"{state['cap']:,} W", font=F['metric'], fill=INK)
    draw.text((x + 24, y + 101), 'fixed power ceiling', font=F['small'], fill=MUTED)
    draw.text((x + 335, y + 55), f"v{state['version']}", font=F['metric'], fill=INK)
    draw.text((x + 335, y + 101), 'last state read', font=F['small'], fill=MUTED)
    wrapped(draw, state['mode'], (x + 24, y + 146), width - 48, 'body')
    actual = bool(state['tasks'])
    tasks = state['tasks'] if actual else state['proposal']
    if tasks:
        bar_x, bar_w, bar_y = x + 198, 329, y + 215
        for tick in (0, 60, 120, 180):
            tx = bar_x + bar_w * tick / 180
            draw.line((tx, bar_y - 8, tx, bar_y + 118), fill=LINE, width=1)
            draw.text((tx - 9, bar_y + 129), str(tick), font=F['tiny'], fill=MUTED)
        for n, task in enumerate(tasks):
            yy = bar_y + n * 41
            draw.text((x + 24, yy + 3), task['appliance'], font=F['small'], fill=INK)
            left, right = bar_x + bar_w * task['start'] / 180, bar_x + bar_w * task['end'] / 180
            draw.rounded_rectangle((left, yy, right, yy + 29), radius=6, fill=GREEN if actual else BLUE)
            label = str(task['watts']) + ' W'
            tw = draw.textlength(label, font=F['tiny'])
            draw.text(((left + right - tw) / 2, yy + 6), label, font=F['tiny'], fill='white')
        draw.text((bar_x + 150, bar_y + 152), 'relative minutes', font=F['tiny'], fill=MUTED)
    else:
        draw.rounded_rectangle((x + 24, y + 209, x + width - 24, y + 299), radius=12, fill='#f4f6f9')
        draw.text((x + 44, y + 228), '0 tasks in the agenda', font=F['head'], fill=INK)
        draw.text((x + 44, y + 264), f"{state['receipts']} local receipt(s)", font=F['small'], fill=MUTED)
    if state['proposal'] and not actual:
        for index, resident in enumerate(('Alice', 'Bob')):
            approved = resident in state['approvals']
            badge(draw, x + 24 + index * 165, y + 378,
                  resident + (': approved' if approved else ': pending'),
                  GREEN if approved else MUTED, '#e7f5ee' if approved else '#eef1f5')
    elif actual:
        peak = max(sum(task['watts'] for task in tasks if task['start'] <= minute < task['end']) for minute in range(180))
        badge(draw, x + 24, y + 378, f'Peak scheduled: {peak:,} W', GREEN, '#e7f5ee')
    elif state['version'] == 2:
        badge(draw, x + 24, y + 378, 'Original task list restored', GREEN, '#e7f5ee')


def frame(scene, local_t, global_t, before, after, index):
    image = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(image)
    draw.text((40, 25), 'Home Accord', font=F['title'], fill=INK)
    badge(draw, 830, 32, 'RECORDED MCP REPLAY', BLUE)
    draw.text((40, 73), 'Real local HTTP · simulated household · no connected devices', font=F['small'], fill=MUTED)
    draw.text((40, 109), scene['title'], font=F['head'], fill=INK)
    event_index = scene['event']
    if event_index is None:
        draw.rounded_rectangle((40, 153, 1240, 580), radius=18, fill='white', outline=LINE)
        if index == 0:
            draw.text((76, 190), 'The agent proposes.', font=F['hero'], fill=INK)
            draw.text((76, 259), 'The household agrees.', font=F['hero'], fill=BLUE)
            draw.text((76, 346), 'Then apply — or undo.', font=F['head'], fill=INK)
            wrapped(draw, 'This execution viewer replays actual server responses. It is not a browser screen recording or a new model run.',
                    (76, 423), 1070, 'body', MUTED)
            badge(draw, 76, 512, '13 exchanges', BLUE)
            badge(draw, 270, 512, '11 tool calls', BLUE)
            badge(draw, 450, 512, '2 expected refusals', RED, '#fff0f0')
        else:
            draw.text((76, 195), 'A change you can inspect.', font=F['hero'], fill=INK)
            draw.text((76, 266), 'A change you can reverse.', font=F['hero'], fill=GREEN)
            wrapped(draw, 'Observed: consent refusal → simulated approvals → committed agenda → verified undo.',
                    (76, 364), 1070, 'head')
            wrapped(draw, 'Python standard library · MCP 2025-11-25 · source and traces included. No Alexa integration, authenticated residents, or appliance execution.',
                    (76, 445), 1060, 'body', MUTED)
            badge(draw, 76, 527, 'Evidence verifier: PASS', GREEN, '#e7f5ee')
    else:
        event = TRACE['events'][event_index]
        draw.rounded_rectangle((40, 153, 640, 580), radius=18, fill='white', outline=LINE)
        draw.text((62, 171), f"EXCHANGE {event_index + 1:02d} / 13", font=F['small'], fill=MUTED)
        timestamp = event['at'].split('T')[1].split('+')[0]
        draw.text((361, 171), timestamp + ' UTC', font=F['tiny'], fill=MUTED)
        request = brief_request(event)
        draw.text((62, 205), 'REQUEST', font=F['small'], fill=BLUE)
        # Reveal the actual recorded request, then its corresponding recorded response.
        characters = int(local_t * 110)
        request_text = '\n'.join(request)
        for row, line in enumerate(request_text[:characters].split('\n')):
            draw.text((62, 234 + row * 25), line, font=F['code'], fill=INK)
        reveal = local_t >= 2.0
        if reveal:
            error = event['response']['result'].get('isError', False)
            color = RED if error else GREEN
            draw.line((62, 391, 617, 391), fill=LINE)
            draw.text((62, 407), 'RESPONSE · HTTP ' + str(event['http_status']), font=F['small'], fill=color)
            response = '\n'.join(brief_response(event))
            response_chars = int((local_t - 2) * 100)
            for row, line in enumerate(response[:response_chars].split('\n')):
                draw.text((62, 440 + row * 25), line, font=F['code'], fill=color if error else INK)
        else:
            draw.text((62, 442), 'Awaiting recorded response…', font=F['small'], fill=MUTED)
        right_panel(draw, after if reveal else before, local_t / scene['duration'])
    draw.rounded_rectangle((40, 599, 1240, 688), radius=14, fill=INK)
    wrapped(draw, scene['caption'], (62, 611), 1152, 'caption', 'white', spacing=4)
    draw.rectangle((40, 701, 1240, 705), fill=LINE)
    draw.rectangle((40, 701, 40 + 1200 * global_t / TOTAL, 705), fill=BLUE)
    return image


def srt_time(seconds):
    millis = int(seconds * 1000)
    return f'{millis // 3600000:02}:{millis // 60000 % 60:02}:{millis // 1000 % 60:02},{millis % 1000:03}'


def main():
    output = ROOT / 'Home_Accord_Demo_138s.mp4'
    command = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo',
               '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
               '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-pix_fmt', 'yuv420p',
               '-movflags', '+faststart', str(output)]
    proc = subprocess.Popen(command, stdin=subprocess.PIPE)
    state = {'known': False, 'version': 0, 'cap': 2500, 'tasks': [], 'proposal': [],
             'approvals': [], 'receipts': 0, 'mode': '', 'notice': ''}
    elapsed = 0
    srt = []
    script = ['# Home Accord — 138-second video script', '',
              'Final video mode: animated execution viewer of a newly executed local HTTP replay.',
              'The previous live-agent interaction supplied the command sequence. This replay performs no new AI inference.',
              'Captions are English and burned into the image. The video has no audio track.', '']
    for index, scene in enumerate(SCENES):
        before = deepcopy(state)
        if scene['event'] is not None:
            state = update_state(state, TRACE['events'][scene['event']])
        after = deepcopy(state)
        srt.append(f"{index + 1}\n{srt_time(elapsed)} --> {srt_time(elapsed + scene['duration'])}\n{scene['caption']}\n")
        script.extend([f"## {elapsed:03d}–{elapsed + scene['duration']:03d} seconds: {scene['title']}",
                       scene['caption'], ''])
        for tick in range(scene['duration'] * FPS):
            t = tick / FPS
            image = frame(scene, t, elapsed + t, before, after, index)
            if tick == min(4 * FPS, scene['duration'] * FPS - 1):
                image.save(ROOT / f'qa_scene_{index:02d}.png')
            proc.stdin.write(image.tobytes())
        elapsed += scene['duration']
        print(f"Rendered scene {index + 1}/{len(SCENES)} at {elapsed}s", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError('ffmpeg encoding failed')
    (ROOT / 'Home_Accord_Demo_en.srt').write_text('\n'.join(srt), encoding='utf-8')
    (ROOT / 'VIDEO_SCRIPT.md').write_text('\n'.join(script), encoding='utf-8')
    print(json.dumps({'duration_seconds': TOTAL, 'output': str(output),
                      'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}), flush=True)


if __name__ == '__main__':
    main()
