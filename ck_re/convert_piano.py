"""convert_piano.py: SF2 -> formato 'zones/waves' do ck_build_new (kind cfx), 5 camadas.

Mapeia o SF2 na grade de keymaps do CFX do CK (804-808 = 5 elementos, 89 zonas cada):
zi 0 = teclas 0-21 (root 21), zi 1-86 = 22..107, zi 87 = 108-120, zi 88 = 121-127.
Cada camada recebe a zona do SF2 que cobre a velocidade central do elemento CFX
(2-66 / 67-85 / 86-109 / 110-124 / 125-127 -> vc 34/76/97/117/126).

- estereo por par L/R (pan ou tipo do sample: 4=L, 2=R);
- 48/35 kHz -> 44,1 kHz; initialAttenuation; normalizacao global de pico; limitador 3 dB;
- sem loop (como Blk Uprght/Astoria): a nota decai naturalmente;
- dedup de wave por (sampleID, atenuacao, shift).

usage: convert_piano.py OUT SF2 [tmax] [allow_up 0|1]
"""
import sys, os, json, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
YC = "/Users/mateusbueno/Downloads/YamahaYC/yc_re/final_2.01.0"
sys.path.insert(0, YC)
from sf2parse import load
from scipy.signal import resample_poly
from scipy.ndimage import maximum_filter1d
from fractions import Fraction
import enc_common as EC

OUT = sys.argv[1]; SF2 = sys.argv[2]
TMAX = float(sys.argv[3]) if len(sys.argv) > 3 else 8.0
ALLOW_UP = (sys.argv[4] != "0") if len(sys.argv) > 4 else True
FS = 44100; CEIL = 0.90; PRE_DB = 3.0; UNIT = 0.00169/3.4466*1.23
EC.MAXFRAMES = 30000
SLOTS = [(804, 34), (805, 76), (806, 97), (807, 117), (808, 126)]
KEYS = [21] + list(range(22, 108)) + [108, 120]          # root de cada uma das 89 zonas

S = load(SF2); raw = open(SF2, 'rb').read(); so = S['smpl'][0]; smp = S['samples']
Z = [z for z in S['insts'][0]['zones'] if 'sampleID' in z]

def side(z):
    p = z.get('pan', 0)
    if p: return -1 if p < 0 else 1
    t = smp[z['sampleID']]['type']
    return -1 if t == 4 else (1 if t == 2 else 0)

def rd(sid):
    s = smp[sid]
    return np.frombuffer(raw, dtype='<i2', count=s['end']-s['start'],
                         offset=so+2*s['start']).astype(np.float64)/32768

_sig = {}
def load_sig(sid, att):
    k = (sid, att)
    if k not in _sig:
        x = rd(sid)*10**(-att/200)
        r = smp[sid]['rate']
        if r != FS:
            f = Fraction(FS, r); x = resample_poly(x, f.numerator, f.denominator)
        _sig[k] = x[:int(TMAX*FS)]
    return _sig[k]

# ---- grupos estereo (par L/R por keyRange+velRange) ----
G = []
for z in Z:
    if side(z) >= 0: continue
    zr = [q for q in Z if q['keyRange'] == z['keyRange'] and q.get('velRange') == z.get('velRange') and side(q) > 0]
    if not zr: continue
    zr = zr[0]
    G.append(dict(key=list(z['keyRange']), vel=list(z.get('velRange', (0, 127))),
                  root=z.get('overridingRootKey', smp[z['sampleID']]['pitch']),
                  L=z['sampleID'], R=zr['sampleID'],
                  attL=z.get('initialAttenuation', 0), attR=zr.get('initialAttenuation', 0)))

# ---- escolha por camada/tecla ----
chosen = {}
for km, vc in SLOTS:
    for zi, k in enumerate(KEYS):
        c = [g for g in G if g['vel'][0] <= vc <= g['vel'][1] and g['key'][0] <= k <= g['key'][1]]
        if not c: c = [g for g in G if g['vel'][0] <= vc <= g['vel'][1]]
        if not c: c = G
        g = min(c, key=lambda g: min(abs(k-g['key'][0]), abs(k-g['key'][1])))
        chosen[(km, zi)] = g

pairs = {}
for g in chosen.values():
    pairs[(g['L'], g['R'], g['attL'], g['attR'])] = g
pair_of = {}
for (km, zi), g in chosen.items():
    pair_of[(km, zi)] = (g['L'], g['R'], g['attL'], g['attR'])

# ---- ganho global ----
pk = 0.0
for g in pairs.values():
    pk = max(pk, np.abs(load_sig(g['L'], g['attL'])).max(), np.abs(load_sig(g['R'], g['attR'])).max())
gain0 = CEIL*10**(PRE_DB/20)/pk

def limit(sig):
    env = np.max(np.abs(np.stack(sig)), 0)
    need = np.minimum(1.0, CEIL/np.maximum(env, 1e-9))
    need = -maximum_filter1d(-need, size=177)
    gain = np.empty(len(env)); gc = 1.0; rel = np.exp(-1/(0.06*FS))
    for t in range(len(env)):
        gc = need[t] if need[t] < gc else min(need[t], 1-(1-gc)*rel); gain[t] = gc
    return [np.clip(x*gain, -CEIL, CEIL)/UNIT for x in sig]

os.makedirs(OUT, exist_ok=True)
blob = open(os.path.join(OUT, 'waves.bin'), 'wb'); pos = 0
waves = {}      # id -> entrada
bykey = {}      # (sid, att, shift) -> id
def put(sid, att, sh, res):
    global pos
    k = (sid, att, sh)
    if k in bykey: return bykey[k]
    wb, n, snr, secs, lp = res
    assert len(wb) % 4096 == 0
    wid = len(waves)
    e = dict(b=n, snr=round(snr, 2), secs=round(secs, 2), shift=sh,
             page_off=pos, pages=len(wb)//4096)
    blob.write(wb); pos += e['pages']; waves[wid] = e; bykey[k] = wid
    return wid

# maior transposicao acima da raiz que cada par vai tocar (limita o upsampling)
maxoff = {}
for (km, zi), g in chosen.items():
    k = (g['L'], g['R'], g['attL'], g['attR'])
    maxoff[k] = max(maxoff.get(k, 0), max(0, KEYS[zi]-g['root']))

pairwave = {}
for pi, key in enumerate(sorted(pairs, key=lambda k: (k[0], k[1], k[2], k[3]))):
    g = pairs[key]
    xs = limit([load_sig(g['L'], g['attL'])*gain0, load_sig(g['R'], g['attR'])*gain0])
    thr = -42.0 if g['root'] <= 60 else -60.0
    sh, res = EC.encode_best(xs, FS, (1.0, 4), ALLOW_UP, thr, max_off=maxoff[key])
    pairwave[key] = (put(g['L'], g['attL'], sh, res[0]), put(g['R'], g['attR'], sh, res[1]))
    if pi % 25 == 0: print('  %d/%d pares' % (pi, len(pairs)), flush=True)

zones = []
for (km, zi), g in sorted(chosen.items()):
    L, R = pairwave[pair_of[(km, zi)]]
    zones.append(dict(km=km, zi=zi, L=L, R=R, root=int(g['root']), fine=0))

blob.close()
json.dump(dict(waves={str(k): v for k, v in waves.items()}, zones=zones,
               total_pages=pos, fs=FS, tmax=TMAX),
          open(os.path.join(OUT, 'index.json'), 'w'), indent=1)
shs = sorted(set(w['shift'] for w in waves.values()))
print('waves', len(waves), 'zones', len(zones), 'pages', pos, 'MB %.2f' % (pos*4096/2**20), 'shifts', shs)
print('b max', max(w['b'] for w in waves.values()), 'snr min %.1f' % min(w['snr'] for w in waves.values()))
