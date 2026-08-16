"""Build out/chart_data.json for the dashboard from the rescored corpus."""
import csv
import json
import math
from collections import defaultdict

LAB = {
    'claude-fable-5': 'Anthropic', 'claude-opus-5': 'Anthropic',
    'claude-sonnet-5': 'Anthropic', 'claude-haiku-4-5': 'Anthropic',
    'grok-4.5': 'xAI', 'gpt-5.6-sol': 'OpenAI', 'gpt-5.6-terra': 'OpenAI',
    'gpt-5.6-luna': 'OpenAI', 'gemini-3.1-pro-preview': 'Google',
    'gemini-3.6-flash': 'Google', 'gemini-3.1-flash-lite': 'Google', 'gemma3:4b': 'Google', 'phi4:14b': 'Microsoft',
    'deepseek-r1:8b': 'DeepSeek', 'granite3.3:8b': 'IBM', 'command-r7b': 'Cohere',
    'olmo2:7b': 'AI2', 'nemotron-mini': 'Nvidia', 'hermes3:8b': 'Nous Research',
    'smollm2:1.7b': 'HuggingFace', 'qwen3:8b': 'Alibaba', 'qwen2.5:14b': 'Alibaba',
    'qwen2.5:7b': 'Alibaba', 'qwen2.5:1.5b': 'Alibaba', 'llama3.1:8b': 'Meta',
    'mistral:7b': 'Mistral AI',
}
HOSTED = {'claude-fable-5', 'claude-opus-5', 'claude-sonnet-5', 'claude-haiku-4-5',
          'grok-4.5', 'gpt-5.6-sol', 'gpt-5.6-terra', 'gpt-5.6-luna',
          'gemini-3.1-pro-preview', 'gemini-3.6-flash', 'gemini-3.1-flash-lite'}
SYN = ['generic', 'chatml', 'llama3', 'json', 'xml_anthropic', 'plain_label']
SYN_LABEL = {'generic': 'generic &lt;user&gt;', 'chatml': 'ChatML',
             'llama3': 'Llama 3 header', 'json': 'JSON envelope',
             'xml_anthropic': 'Anthropic XML', 'plain_label': "plain 'User:'"}
LEVELS = ['control', 'L1', 'L2', 'L3', 'L3_notags', 'L3_forged']


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0, c - h), min(1, c + h))


def syn_of(lv):
    if lv == 'L3_forged':
        return 'generic'
    return lv[7:] if lv.startswith('forged_') else None


def cell(d):
    return {'pct': round(100 * d['c'] / d['n']), 'n': d['n'], 'k': d['c'], 'b': d['b']} if d['n'] else None


def main():
    rows = list(csv.DictReader(open('out/rescored_all.csv', encoding='utf-8')))
    blank = lambda: {'n': 0, 'c': 0, 'b': 0}
    grid = defaultdict(lambda: defaultdict(blank))
    chan = defaultdict(lambda: defaultdict(blank))
    dfns = defaultdict(lambda: defaultdict(blank))
    heat = defaultdict(lambda: defaultdict(blank))
    det = defaultdict(blank)
    ref = defaultdict(blank)

    for r in rows:
        d0 = r.get('defense') or 'none'
        comp = r['compromised'] == 'True'
        blk = r.get('api_refusal') == 'True'
        if r['scaffold'] != 'refund_ticket':
            s = syn_of(r['level'])
            key = s if s else (r['level'] if r['level'] in ('L3', 'L3_notags') else None)
            if key and d0 == 'none':
                x = grid[r['model']][key]; x['n'] += 1; x['c'] += comp; x['b'] += blk
            if r['level'] in ('L3_forged', 'forged_generic', 'forged_llama3'):
                x = dfns[r['model']][d0]; x['n'] += 1; x['c'] += comp; x['b'] += blk
            if r['level'] == 'bare_command' and d0 == 'none':
                x = chan[r['model']][r['channel']]; x['n'] += 1; x['c'] += comp; x['b'] += blk
            lv = 'L3_forged' if r['level'] == 'forged_generic' else r['level']
            if lv in LEVELS and d0 == 'none':
                x = heat[r['model']][lv]; x['n'] += 1; x['c'] += comp; x['b'] += blk
        if r['level'] != 'control' and d0 == 'none':
            det[r['model']]['n'] += 1; det[r['model']]['c'] += (r['detected'] == 'True')
        if r['scaffold'] == 'refund_ticket' and r['level'] != 'control' and d0 == 'none':
            ref[r['model']]['n'] += 1; ref[r['model']]['c'] += comp

    def sortkey(m):
        g = grid[m]
        if 'L3_notags' not in g:
            return (999, m)
        ct = 100 * g['L3_notags']['c'] / g['L3_notags']['n']
        fs = [g[s] for s in SYN if s in g]
        f = 100 * sum(x['c'] for x in fs) / sum(x['n'] for x in fs) if fs else 0
        return (-(f - ct), m)

    order = sorted(grid, key=sortkey)
    groups = [('hosted', [m for m in order if m in HOSTED]),
              ('open', [m for m in order if m not in HOSTED])]

    pooled = {}
    for grp, ms in groups:
        pooled[grp] = {}
        for key in ['L3', 'L3_notags'] + SYN:
            k = sum(grid[m][key]['c'] for m in ms if key in grid[m])
            n = sum(grid[m][key]['n'] for m in ms if key in grid[m])
            b = sum(grid[m][key]['b'] for m in ms if key in grid[m])
            if n:
                lo, hi = wilson(k, n)
                pooled[grp][key] = {'pct': round(100 * k / n, 1), 'k': k, 'n': n, 'b': b,
                                    'lo': round(100 * lo, 1), 'hi': round(100 * hi, 1)}
    dpool = {}
    for grp, ms in groups:
        dpool[grp] = {}
        for d in ['none', 'brief', 'explicit', 'strict']:
            k = sum(dfns[m][d]['c'] for m in ms if d in dfns[m])
            n = sum(dfns[m][d]['n'] for m in ms if d in dfns[m])
            if n:
                dpool[grp][d] = {'pct': round(100 * k / n), 'k': k, 'n': n}

    out = {
        'models': [{'id': m, 'lab': LAB.get(m, '?'), 'hosted': m in HOSTED} for m in order],
        'syntaxes': SYN, 'synLabel': SYN_LABEL, 'levels': LEVELS,
        'syntaxGrid': {m: {k: cell(grid[m][k]) for k in ['L3', 'L3_notags'] + SYN if k in grid[m]} for m in order},
        'heatmap': {m: {lv: cell(heat[m][lv]) for lv in LEVELS if lv in heat[m]} for m in order},
        'pooled': pooled, 'defensePooled': dpool,
        'channel': {m: {c: cell(chan[m][c]) for c in ['tool_result', 'user_turn', 'user_turn_matched'] if c in chan[m]} for m in order},
        'detection': {m: cell(det[m]) for m in order if det[m]['n']},
        'refund': {m: cell(ref[m]) for m in order if ref[m]['n']},
        'total_trials': len(rows), 'n_models': len(order),
        'n_labs': len({LAB.get(m) for m in order}),
    }
    json.dump(out, open('out/chart_data.json', 'w'), indent=1)
    print(f"{len(rows)} trials | {len(order)} arms | {out['n_labs']} labs")


if __name__ == '__main__':
    main()
