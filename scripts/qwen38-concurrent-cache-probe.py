#!/usr/bin/env python3
"""Check two independently cached 250K contexts on the isolated AutoRound seat.

Requires loopback :8888, model qwen3.8-flash-next-autoround, the development
cache-reset endpoint, and capacity for both contexts. Submits two requests
together, verifies their distinct answers, then requires faster warm repeats.
This does not assume that the engine processes their cold prefills in parallel.
Never run cache reset while application clients use the seat.

Usage: python3 scripts/qwen38-concurrent-cache-probe.py --evidence /new/directory
"""

import argparse, importlib.util, json, random, threading, time
from pathlib import Path
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
spec = importlib.util.spec_from_file_location('probe', Path(__file__).with_name('qwen38-seat-probe.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
a = argparse.ArgumentParser()
a.add_argument('--evidence', type=Path, required=True)
opt = a.parse_args()
opt.evidence.mkdir(parents=True, exist_ok=False)
args = SimpleNamespace(base_url='http://127.0.0.1:8888', key_env='QWEN38_API_KEY', model='qwen3.8-flash-next-autoround', evidence=opt.evidence)
control = m.Probe(args)
control.reset_prefix_cache()
jobs = []
for index in range(2):
    rng = random.Random(9810 + index)
    expected = ['cobalt-731', 'amber-942'][index]
    filler = ' '.join((rng.choice('ledger invoice annex schedule vendor contract tax paid'.split()) + str(rng.randrange(10000)) for _ in range(250000)))
    lo, hi = (0, len(filler))
    for _ in range(24):
        size = (lo + hi) // 2
        messages = [{'role': 'user', 'content': f'Independent record {index}. alpha={expected}.\n' + filler[:size] + '\nReply only with this record alpha value.'}]
        count = control.json_request('/tokenize', {'model': args.model, 'messages': messages, 'add_generation_prompt': True, 'chat_template_kwargs': {'enable_thinking': False}})['count']
        if 250000 <= count <= 250128:
            break
        if count < 250000:
            lo = size + 1
        else:
            hi = size - 1
    else:
        raise RuntimeError('cannot size concurrent prompt')
    jobs.append((index, expected, messages, count))
    print('Prepared', index, count, 'tokens', flush=True)
results = []
for phase in ['cold', 'warm']:
    barrier = threading.Barrier(2)

    def worker(job):
        i, expected, messages, count = job
        probe = m.Probe(args)
        barrier.wait()
        d = probe.chat(messages, f'concurrent-{phase}-{i}', max_tokens=64)
        assert d['content'].strip() == expected, 'incorrect independent-context recall'
        assert abs(d['usage']['prompt_tokens'] - count) <= 128 and d['usage']['prompt_tokens'] >= 250000
        return d
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(worker, jobs))
    results.append(rows)
    (opt.evidence / f'{phase}.json').write_text(json.dumps(rows, indent=2) + '\n')
for cold, warm in zip(*results):
    assert warm['ttft_s'] <= cold['ttft_s'] * 0.5, 'retained independent prefixes did not accelerate repeats'
(opt.evidence / 'result.json').write_text(json.dumps({'status': 'PASS', 'simultaneous_requests': 2, 'target_tokens_each': 250000, 'results': results}, indent=2) + '\n')
print('PASS two independent 250K requests and warm repeats', flush=True)
