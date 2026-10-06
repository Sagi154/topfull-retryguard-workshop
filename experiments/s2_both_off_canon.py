"""Canonical unfiltered scorer for S2 both-off runs. One schema, every service, every edge."""
import csv, json, os, sys, statistics as st
from collections import defaultdict
from datetime import datetime

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results', 'campaign_48', 'S2_sustained_overload', 'baseline_no_topfull_sustained_overload_run%d')
CTRL = ['adservice', 'cartservice', 'checkoutservice', 'currencyservice', 'emailservice',
        'paymentservice', 'productcatalogservice', 'recommendationservice', 'shippingservice']


def ts(s):
    return datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ').timestamp()


def rd(p):
    return list(csv.DictReader(open(p))) if os.path.exists(p) else None


def score(n, clip600=False):
    d = ROOT % n
    out = dict(run=n, svc={}, edges={}, loc={}, q={})
    inb = rd(d + '/service_inbound.csv')
    if inb:
        by = defaultdict(list)
        t0 = ts(inb[0]['timestamp'])
        for r in inb:
            if clip600 and ts(r['timestamp']) - t0 > 600:
                continue
            by[r['service']].append(r)
        has_res = 'resets' in inb[0]
        for s, rows in by.items():
            rows = rows[:-5] if len(rows) > 5 else rows
            streak = cur = high = 0
            for a, b in zip(rows, rows[1:]):
                dt = float(b['total']) - float(a['total'])
                d5 = float(b['5xx']) - float(a['5xx'])
                dr = (float(b['resets']) - float(a['resets'])) if has_res else 0
                if dt > 0 and (d5 + dr) / dt > 0.20:
                    cur += 1; high += 1; streak = max(streak, cur)
                else:
                    cur = 0
            out['svc'][s] = dict(streak=streak, high=high, polls=len(rows))
        cts = [ts(r['timestamp']) for r in by.get('checkoutservice', [])]
        gaps = [b - a for a, b in zip(cts, cts[1:])]
        if gaps:
            out['q']['gap_med'] = st.median(gaps)
            out['q']['gap2_pct'] = round(100 * sum(g >= 1.5 for g in gaps) / len(gaps))
        out['q']['span'] = ts(inb[-1]['timestamp']) - t0
        out['q']['has_resets'] = has_res
    det = rd(d + '/topfull_detect.csv')
    if det:
        by = defaultdict(list)
        for r in det:
            by[r['service']].append(r)
        for s, rows in by.items():
            x = out['svc'].setdefault(s, {})
            x['ov'] = sum(int(float(r['overloaded'])) for r in rows)
            x['dticks'] = len(rows)
            u = sorted(float(r['utilization']) for r in rows)
            x['umax'] = u[-1]
    res = rd(d + '/resource_usage.csv')
    if res:
        by = defaultdict(list)
        for r in res:
            by[r['service']].append(int(float(r['replica_count'])))
        for s, v in by.items():
            out['svc'].setdefault(s, {})['rzero'] = sum(1 for x in v if x == 0)
            out['svc'][s]['rmode'] = st.mode(v)
    ed = rd(d + '/service_edges.csv')
    if ed:
        by = defaultdict(list)
        for r in ed:
            by[(r['caller'], r['target'])].append(float(r['retry']))
        for k, v in by.items():
            dl = sum(max(0, b - a) for a, b in zip(v, v[1:]))
            if dl > 0:
                out['edges'][k] = dl
    for api in ['getproduct', 'postcheckout', 'getcart', 'postcart', 'emptycart']:
        L = rd(d + '/%s.csv' % api)
        if not L:
            continue
        L = L[30:-5]
        rps = sum(float(r['RPS']) for r in L); fl = sum(float(r['Fail']) for r in L)
        gp = st.mean(float(r['Goodput']) for r in L)
        out['loc'][api] = dict(gp=gp, fail=fl / rps if rps else None, p95=st.mean(float(r['Latency95']) for r in L), rows=len(L) + 35)
    return out


if __name__ == '__main__':
    lo, hi = int(sys.argv[1]), int(sys.argv[2])
    res = {}
    for n in range(lo, hi + 1):
        if os.path.isdir(ROOT % n):
            o = score(n)
            o['edges'] = {'%s>%s' % k: v for k, v in o['edges'].items()}
            res[n] = o
    json.dump(res, open('s2_canon_%d_%d.json' % (lo, hi), 'w'))
    print('done', len(res))
