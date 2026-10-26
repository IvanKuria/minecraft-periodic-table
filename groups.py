"""Step 2: sort the elements the way Mendeleev did.

Mendeleev didn't group elements by what they look like. He grouped them by what they combine into: sodium and
potassium both mix with chlorine and make basically the same thing, so they go together.

Here every recipe gets written in elements (an iron ingot counts as iron, sticks count as wood), and then one element
gets blanked out. A pickaxe is three of something plus two sticks. Whatever else fits in that blank makes the same
kind of compound. Elements that keep fitting the same blanks end up in the same group. The groups only get names
after they show up.

    python groups.py   ->  results/groups.json
"""
import itertools
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from recipes import GAME, short

ROOT = Path(__file__).resolve().parent
LINK = .12                 # average-linkage threshold (the groups hold steady from .06 to .3)
# effect ingredients and modifiers from the brewing stand (net.minecraft...VanillaBrewingProvider)
BREW_EFFECT = ['sugar_cane', 'rabbit_foot', 'spider_eye', 'pufferfish', 'ghast_tear', 'phantom_membrane', 'breeze_rod', 'blaze_rod', 'stone']
BREW_MODIFIER = ['redstone', 'glowstone_dust', 'gunpowder']
NAMES = {'raw_iron': 'Tool-formers', 'emerald': 'Packers', 'quartz': 'Masonry', 'bone': 'Colourants'}


def strip(item):
    return re.match(r'(waxed_)?(exposed_|weathered_|oxidized_)?(stripped_)?(.+)', item).group(4)


def recipes_raw():
    tags = {p.stem: json.load(open(p))['values'] for p in (GAME / 'tags/item').glob('*.json')}

    def expand(x, seen=()):
        x = x['id'] if isinstance(x, dict) else x
        if isinstance(x, list):
            return [o for y in x for o in expand(y, seen)]
        if x.startswith('#'):
            k = short(x[1:])
            return [o for v in tags.get(k, []) if k not in seen for o in expand(v, seen + (k,))]
        return [short(x)]
    out = []
    for p in sorted((GAME / 'recipe').glob('*.json')):
        j = json.load(open(p))
        kind = j['type'].split(':')[1]
        res = j.get('result')
        res = res.get('id', '') if isinstance(res, dict) else res or ''
        if not res:
            continue
        name = strip(short(res))
        if kind == 'crafting_shaped':
            out.append(('shaped', name, j['pattern'], {k: expand(v) for k, v in j['key'].items()}))
        elif kind == 'crafting_shapeless':
            out.append(('shapeless', name, None, [expand(v) for v in j['ingredients']]))
        elif kind in ('smelting', 'blasting', 'smoking', 'campfire_cooking', 'stonecutting'):
            out.append(('heat', name, None, [expand(j['ingredient'])]))
        elif kind == 'smithing_transform':
            out.append(('smithing', name, None, [expand(j[k]) for k in ('template', 'base', 'addition') if k in j]))
    return out


def main():
    elements = json.load(open(ROOT / 'results/elements.json'))
    recs = recipes_raw()
    outputs = {r[1] for r in recs}
    # what each item is made of, when it's made of exactly one element (black dye = ink sac OR wither rose)
    made_of = defaultdict(set)
    for e in elements:
        for m in [e['element']] + e['members']:
            if m == e['element'] or m not in outputs:
                made_of[m].add(e['element'])
    radical = False

    def slot(opts):
        s = set()
        for o in opts:
            s |= made_of.get(strip(o), set())
        if not s and radical:
            s = {'~' + strip(sorted(opts)[0])}         # a compound ingredient (a book, a bucket) stays as itself
        return s

    def slots_of(r):
        return [r[3][c] for row in r[2] for c in row if c != ' '] if r[0] == 'shaped' else r[3]
    changed = True
    while changed:
        changed = False
        for r in recs:
            sl = [slot(o) for o in slots_of(r)]
            if not sl or not all(sl):
                continue
            common = set.intersection(*sl)
            if all(s == common for s in sl) and not common <= made_of[r[1]]:
                made_of[r[1]] |= common
                changed = True

    radical = True
    formulas = defaultdict(lambda: defaultdict(set))   # element -> {formula with that element blanked: {products}}
    for r in recs:
        kind, out = r[0], r[1]
        if kind == 'heat':
            continue                                   # heating one thing isn't combining
        if kind == 'shaped':
            chars = sorted({c for row in r[2] for c in row if c != ' '})
            ce = {c: slot(r[3][c]) for c in chars}
            if not all(ce.values()):
                continue
            for c in chars:
                for x in [y for y in ce[c] if not y.startswith('~')]:
                    if any(x in ce[d] for d in chars if d != c):
                        continue
                    grid = tuple(''.join('X' if ch == c else (' ' if ch == ' ' else 'o') for ch in row) for row in r[2])
                    rest = tuple(sorted(tuple(sorted(ce[d])) for d in chars if d != c for row in r[2] for ch in row if ch == d))
                    formulas[x][('shaped', grid, rest)].add(out)
        else:
            sl = [slot(o) for o in r[3]]
            if not all(sl):
                continue
            for i, s in enumerate(sl):
                for x in [y for y in s if not y.startswith('~')]:
                    rest = tuple(sorted(tuple(sorted(q)) for k, q in enumerate(sl) if k != i and x not in q))
                    formulas[x][(kind, sum(1 for q in sl if x in q), rest)].add(out)
    for x in BREW_EFFECT:
        formulas[x][('brew', 'awkward')].add('potion')
    for x in BREW_MODIFIER:
        formulas[x][('brew', 'modifier')].add('potion')
    formulas['nether_wart'][('brew', 'water')].add('awkward_potion')

    T = {x: set(v) for x, v in formulas.items()}
    combiners = sorted(T)

    def sim(a, b):
        shared = len(T[a] & T[b])
        return shared / len(T[a] | T[b]) if shared >= 2 else 0
    clusters = [[e] for e in combiners]

    def link(A, B):
        return sum(sim(a, b) for a in A for b in B) / (len(A) * len(B))
    while True:
        best = max(((link(A, B), i, j) for (i, A), (j, B) in itertools.combinations(enumerate(clusters), 2)), default=(0,))
        if best[0] < LINK:
            break
        _, i, j = best
        clusters[i] += clusters[j]
        del clusters[j]
    clusters.sort(key=len, reverse=True)

    groups = []
    for g in clusters:
        if len(g) < 2:
            continue
        shared = Counter(k for e in g for k in T[e]).most_common(1)[0][0]
        example = sorted(set.intersection(*(formulas[e][shared] for e in g)) or formulas[g[0]][shared])[:3]
        name = next((NAMES[e] for e in g if e in NAMES), 'Pair' if len(g) == 2 else 'Group')
        groups.append({'name': name, 'elements': sorted(g), 'shared_formula': str(shared), 'example_products': example})
    inert = sorted(e['element'] for e in elements if e['element'] not in T)
    unplaced = sorted(g[0] for g in clusters if len(g) == 1)
    json.dump({'groups': groups, 'inert': inert, 'no_group_yet': unplaced}, open(ROOT / 'results/groups.json', 'w'), indent=1)
    for g in groups:
        print(f"{g['name']:12s} {len(g['elements']):2d}  {', '.join(g['elements'])}")
    print(f'inert {len(inert)}, no group yet {len(unplaced)}')


if __name__ == '__main__':
    main()
