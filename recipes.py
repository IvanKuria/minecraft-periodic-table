"""Reads the game's own data files (unpacked by extract.py): every recipe, the item tags they use, and the loot tables."""
import json
import re
from pathlib import Path

GAME = Path(__file__).resolve().parent / 'game' / 'data' / 'minecraft'


def short(item):
    """minecraft:iron_ingot -> iron_ingot"""
    return item.split(':')[-1]


def alias(item):
    """Things the world changes for you, not a recipe: stripped logs and weathered or waxed copper count as the original."""
    m = re.match(r'minecraft:stripped_(.+)', item)
    if m:
        return 'minecraft:' + m.group(1)
    m = re.match(r'minecraft:(waxed_)?(exposed|weathered|oxidized)_(.+)', item)
    if m:
        rest = 'copper_block' if m.group(3) == 'copper' else m.group(3)
        return 'minecraft:' + ('waxed_' if m.group(1) else '') + rest
    return item


def load():
    """Every recipe as (output, count, [list of acceptable items per ingredient slot], recipe type, file name)."""
    tags = {}
    for p in (GAME / 'tags/item').glob('*.json'):
        tags['minecraft:' + p.stem] = json.load(open(p)).get('values', [])

    def expand(tag, seen=()):
        out = []
        for v in tags.get(tag, []):
            v = v['id'] if isinstance(v, dict) else v
            if v.startswith('#'):
                if v[1:] not in seen:
                    out += expand(v[1:], seen + (tag,))
            else:
                out.append(v)
        return out

    def options(ing):
        if isinstance(ing, str):
            return expand(ing[1:]) if ing.startswith('#') else [ing]
        if isinstance(ing, list):
            return [x for i in ing for x in options(i)]
        if 'item' in ing:
            return [ing['item']]
        if 'tag' in ing:
            return expand('minecraft:' + ing['tag'].split(':')[-1])
        return []

    recipes = []
    for p in sorted((GAME / 'recipe').glob('*.json')):
        r = json.load(open(p))
        kind = r.get('type', '').split(':')[-1]
        res = r.get('result')
        if not res:
            continue
        out = res if isinstance(res, str) else res.get('id') or res.get('item')
        count = 1 if isinstance(res, str) else res.get('count', 1)
        if kind == 'crafting_shaped':
            slots = [options(r['key'][ch]) for row in r['pattern'] for ch in row if ch != ' ']
        elif kind == 'crafting_shapeless':
            slots = [options(i) for i in r['ingredients']]
        elif kind in ('smelting', 'blasting', 'smoking', 'campfire_cooking', 'stonecutting'):
            slots = [options(r['ingredient'])]
        elif kind == 'smithing_transform':
            slots = [options(r['template']), options(r['base']), options(r['addition'])]
        elif kind == 'crafting_transmute':
            slots = [options(r['input']), options(r['material'])]
        else:
            continue
        if slots and all(slots):
            recipes.append((out, count, slots, kind, p.stem))
    return recipes, tags


def loot_drops(node):
    """(item, needs_special_tool) for every item in a loot table. Special tool = silk touch or shears."""
    out = []
    if isinstance(node, dict):
        if node.get('type') == 'minecraft:item' and 'name' in node:
            cond = json.dumps(node.get('conditions', [])) + json.dumps(node.get('condition', ''))
            out.append((node['name'], 'silk' in cond or 'shear' in cond))
        for v in node.values():
            out += loot_drops(v)
    elif isinstance(node, list):
        for v in node:
            out += loot_drops(v)
    return out


def loot_tables(folder):
    """{table name: [(item, needs_special_tool)]} for one loot table folder, e.g. 'blocks'."""
    base = GAME / 'loot_table' / folder
    return {str(p.relative_to(base).with_suffix('')): loot_drops(json.load(open(p))) for p in sorted(base.rglob('*.json'))}
