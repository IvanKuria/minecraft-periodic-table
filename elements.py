"""Step 1: find Minecraft's elements.

An element is anything you can't make out of something simpler. So every item gets broken down, recipe by recipe,
until it hits stuff no recipe can make. Then the rules from the video:
  1. it has to come from nature (a block, mob, fishing or gameplay drop, not chest loot)
  2. it's whatever actually lands in your hand (mining diamond ore gives you a diamond, so the diamond counts)
  3. it isn't something people made (bells, potions, music discs...)
  4. it isn't just something else that changed (dead coral, grass on dirt, stripped logs, oxidized copper)
Isotopes: items a recipe accepts interchangeably (all twelve logs) share one box. Flowers only share a box when they
make the same dye.

    python elements.py   ->  results/elements.json
"""
import json
import re
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

from recipes import alias, load, loot_drops, loot_tables, short

ROOT = Path(__file__).resolve().parent
PREFER = ('minecraft:oak_', 'minecraft:cobblestone', 'minecraft:sand', 'minecraft:soul_sand', 'minecraft:white_', 'minecraft:stone')


def formulas(recipes):
    """Break every item down to the things nothing can make. Returns {item: {element: amount}}.

    Some items only show up in loops (9 diamonds make a diamond block, the block gives back 9 diamonds), so breaking
    them down never finishes. Inside each loop the element is the one the world hands you some other way."""
    ores = re.compile(r'minecraft:(deepslate_)?\w*_ore$|minecraft:ancient_debris$')
    rs = []
    for out, cnt, slots, kind, name in recipes:
        slots = [sorted({alias(o) for o in opts}) for opts in slots]
        if kind in ('smelting', 'blasting') and all(ores.match(o) and o != 'minecraft:ancient_debris' for o in slots[0]):
            continue                                       # smelting an ore block: you'd have the drop, not the block
        rs.append((alias(out), cnt, slots))
    made = {r[0] for r in rs}
    used = {o for r in rs for opts in r[2] for o in opts}
    comp = {it: {it: Fraction(1)} for it in used - made}

    def mass(c):
        return sum(c.values())

    def relax():
        changed = True
        while changed:
            changed = False
            for out, cnt, slots in rs:
                total = defaultdict(Fraction)
                for opts in slots:
                    known = [o for o in opts if o in comp]
                    if not known:
                        break
                    pick = min(known, key=lambda o: (mass(comp[o]), not o.startswith(PREFER), o))
                    for e, n in comp[pick].items():
                        total[e] += n
                else:
                    if out in total:
                        continue                           # ingot -> block -> ingot is a loop, not a formula
                    cand = {e: n / cnt for e, n in total.items()}
                    cur = comp.get(out)
                    if cand != cur and (cur is None or (cur != {out: 1} and mass(cand) < mass(cur))):
                        comp[out] = cand
                        changed = True

    sources = defaultdict(set)
    for folder, kind in (('blocks', 'mined'), ('entities', 'mob'), ('chests', 'loot'), ('archaeology', 'loot'),
                         ('shearing', 'mob'), ('spawners', 'loot'), ('equipment', 'mob'), ('gameplay', 'other')):
        for drops in loot_tables(folder).values():
            for item, special in drops:
                if not special:
                    sources[item].add(kind)
    dropped_by_other = {item for table, drops in loot_tables('blocks').items() for item, special in drops
                        if not special and item != 'minecraft:' + table}
    relax()
    while True:
        left = {r[0] for r in rs if r[0] not in comp}
        if not left:
            break
        needs = defaultdict(set)
        for out, cnt, slots in rs:
            if out in left:
                for opts in slots:
                    if not any(o in comp for o in opts):
                        needs[out] |= {o for o in opts if o in left}

        def reach(a):
            seen, todo = set(), [a]
            while todo:
                for y in needs[todo.pop()]:
                    if y not in seen:
                        seen.add(y)
                        todo.append(y)
            return seen
        loops = [x for x in left if x in reach(x)]
        pick = min(loops or left, key=lambda x: (x not in dropped_by_other, not (sources.get(x, set()) & {'mob', 'loot'}), len(reach(x)), x))
        comp[pick] = {pick: Fraction(1)}
        relax()
    return comp


def own_drop(block):
    p = ROOT / 'game/data/minecraft/loot_table/blocks' / f'{block}.json'
    if not p.exists():
        return None
    return {short(item) for item, special in loot_drops(json.load(open(p))) if not special}


MADE = re.compile(r'anvil|^bell$|shulker_box|potion|tipped_arrow|ominous_bottle|totem|music_disc|statue|smithing_template|'
                  r'horse_armor|nautilus_armor|chainmail|petrified|heavy_core|bee_nest|^player_head$')
CHANGED = re.compile(r'_concrete$|^stripped_|^(waxed_)?(exposed|weathered|oxidized)_|^carved_pumpkin$')
GREW = re.compile(r'^dead_|_amethyst_bud$|^amethyst_cluster$|^(grass_block|mycelium|podzol|rooted_dirt)$|_nylium$|'
                     r'^mushroom_stem$|_mushroom_block$|^warped_wart_block$|^gilded_blackstone$|^sculk_(vein|catalyst|shrieker|sensor)$')
# versions of the same thing that only differ by species, colour or size share one box
VARIANTS = [
    (r'_sapling$|^mangrove_propagule$|^azalea$|^flowering_azalea$', 'sapling'), (r'_leaves$', 'leaves'), (r'_log$|_stem$', 'log'),
    (r'(brain|bubble|fire|horn|tube)_coral$', 'coral'), (r'(brain|bubble|fire|horn|tube)_coral_block$', 'coral_block'),
    (r'(brain|bubble|fire|horn|tube)_coral_fan$', 'coral_fan'), (r'_head$|_skull$', 'mob_head'), (r'_froglight$', 'froglight'),
    (r'^(blue_|brown_)?egg$|^(sniffer|turtle)_egg$', 'egg'),
    (r'^(short_grass|fern|bush|short_dry_grass|tall_dry_grass|red_shrub|firefly_bush|dead_bush|nether_sprouts)$', 'grass'),
    (r'^(crimson|warped)_roots$', 'nether_roots'), (r'^(crimson|warped)_fungus$', 'fungus'),
    (r'^(twisting|weeping)_vines$|^vine$|^glow_lichen$|^hanging_roots$|^pale_hanging_moss$', 'vine'),
    (r'^(allium|azure_bluet|blue_orchid|cornflower|dandelion|lilac|lily_of_the_valley|orange_tulip|oxeye_daisy|peony|'
     r'pink_petals|pink_tulip|pitcher_plant|poppy|red_tulip|rose_bush|sunflower|torchflower|white_tulip|wither_rose|'
     r'cactus_flower|closed_eyeblossom|open_eyeblossom|wildflowers|spore_blossom)$', 'flower'),
    (r'^(big|small)_dripleaf$', 'dripleaf'), (r'_mushroom$', 'mushroom'), (r'_moss_block$|^moss_block$', 'moss'),
    (r'^(red_)?sand$', 'sand'), (r'^soul_(sand|soil)$', 'soul_sand'), (r'^(torchflower|pitcher_pod|wheat|beetroot)_seeds$|^pitcher_pod$', 'seeds'),
]


def main():
    recipes, _ = load()
    comp = formulas(recipes)
    unmakeable = {short(e) for c in comp.values() for e in c}

    # 1. from nature: block, mob, shearing, gameplay and fishing drops that don't need silk touch or shears
    nature = set()
    for folder in ('blocks', 'entities', 'gameplay', 'shearing'):
        for drops in loot_tables(folder).values():
            nature |= {short(item) for item, special in drops if not special}

    made_by = defaultdict(set)
    for out, cnt, slots, kind, name in recipes:
        made_by[short(out)].add(frozenset(short(x) for opts in slots for x in opts))

    def makeable(it):
        for ins in made_by.get(it, ()):
            if it in ins or all(i in (f'{it}_block', it + 's_block') for i in ins):
                continue                                   # unpacking a diamond block isn't making a diamond
            return True
        return False

    candidates = sorted(i for i in nature if (i in unmakeable or not makeable(i)) and not CHANGED.search(i) and i != 'air')

    # isotopes: anything one recipe slot accepts interchangeably
    parent = {e: e for e in candidates}

    def root(x):
        while parent[x] != x:
            x = parent[x]
        return x
    for out, cnt, slots, kind, name in recipes:
        for opts in slots:
            same = [short(x) for x in opts if short(x) in parent]
            for x in same[1:]:
                parent[root(x)] = root(same[0])
    family = defaultdict(list)
    for e in candidates:
        family[root(e)].append(e)

    # 2. what lands in your hand, 3. not made by someone, 4. not just something else that changed
    keep = [e for e in candidates if (own_drop(e) is None or e in own_drop(e)) and not MADE.search(e) and not GREW.search(e)]
    boxes = {}
    for e in keep:
        r = root(e)
        name = next((n for pat, n in VARIANTS if re.search(pat, e)), None) or (r if len(family[r]) > 1 else e)
        boxes.setdefault(name, []).append(e)

    # flowers only share a box when they make the same dye
    dye_of = {}
    for out, cnt, slots, kind, name in recipes:
        if short(out).endswith('_dye') and len(slots) == 1:
            for x in slots[0]:
                dye_of.setdefault(short(x), short(out))
    for fl in boxes.pop('flower'):
        key = dye_of[fl].replace('_dye', '') + '_flower' if fl in dye_of else 'flower'
        boxes.setdefault(key, []).append(fl)
    boxes['stone'] = boxes.pop('blackstone')               # cobblestone, blackstone, cobbled deepslate
    boxes['snowball'] = boxes.pop('snowball') + boxes.pop('snow')

    out = [{'element': k, 'members': sorted(v)} for k, v in sorted(boxes.items())]
    (ROOT / 'results').mkdir(exist_ok=True)
    json.dump(out, open(ROOT / 'results/elements.json', 'w'), indent=1)
    json.dump({short(k): {short(e): str(n) for e, n in v.items()} for k, v in sorted(comp.items())}, open(ROOT / 'results/formulas.json', 'w'), indent=0)
    print(f'{len(recipes)} recipes, {len(candidates)} natural things nothing can make, {len(out)} elements')


if __name__ == '__main__':
    main()
