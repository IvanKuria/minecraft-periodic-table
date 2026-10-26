"""Step 4: draw the table. Each column is a group from groups.py. Icons come from your game's own textures.

    python render.py   ->  table.png
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
TEX = ROOT / 'game/assets/minecraft/textures'
BEBAS = str(ROOT / 'fonts/BebasNeue-Regular.ttf')

COLOURS = {'Tool-formers': (144, 202, 249), 'Packers': (128, 203, 196), 'Masonry': (224, 224, 224), 'Colourants': (248, 187, 208),
           'Pairs': (255, 224, 178), 'Inert': (179, 157, 219), 'No group yet': (245, 245, 245)}
BLURBS = {'Tool-formers': 'X + WOOD = TOOLS', 'Packers': 'BLOCKS ONLY', 'Masonry': 'SLABS + STAIRS', 'Colourants': 'X + 8 SAND = STAINED GLASS',
          'Pairs': 'SWAP FOR EACH OTHER', 'Inert': 'FORMS NOTHING'}
WIDTH = {'Tool-formers': 1, 'Packers': 1, 'Masonry': 1, 'Colourants': 2, 'Pairs': 2, 'Inert': 3}
ORDER = {'Tool-formers': ['stone', 'raw_copper', 'raw_iron', 'raw_gold', 'diamond'], 'Packers': ['emerald', 'kelp', 'slime_ball', 'coal']}

# which texture stands for each element, and nicer names
ICON = {'log': 'oak_log', 'sapling': 'oak_sapling', 'mushroom': 'red_mushroom', 'fungus': 'crimson_fungus', 'nether_roots': 'crimson_roots',
        'moss': 'moss_block', 'grass': 'short_grass', 'coral': 'tube_coral', 'coral_fan': 'tube_coral_fan', 'seeds': 'wheat_seeds',
        'dripleaf': 'big_dripleaf', 'froglight': 'ochre_froglight', 'stone': 'cobblestone', 'red_flower': 'poppy',
        'yellow_flower': 'dandelion', 'orange_flower': 'orange_tulip', 'pink_flower': 'pink_tulip', 'magenta_flower': 'allium',
        'light_blue_flower': 'blue_orchid', 'light_gray_flower': 'azure_bluet', 'white_flower': 'lily_of_the_valley',
        'blue_flower': 'cornflower', 'black_flower': 'wither_rose', 'gray_flower': 'closed_eyeblossom', 'cyan_flower': 'pitcher_plant',
        'flower': 'spore_blossom'}
NAMES = {'log': 'Wood', 'raw_iron': 'Iron', 'raw_gold': 'Gold', 'raw_copper': 'Copper', 'clay_ball': 'Clay', 'glowstone_dust': 'Glowstone',
         'lapis_lazuli': 'Lapis', 'amethyst_shard': 'Amethyst', 'pointed_dripstone': 'Dripstone', 'sulfur_spike': 'Sulfur',
         'snowball': 'Snow', 'mob_head': 'Mob Head', 'flower': 'Spore Blossom', 'stone': 'Cobblestone', 'wet_sponge': 'Sponge',
         'prismarine_shard': 'Prismarine', 'prismarine_crystals': 'Prism. Crystal', 'nether_roots': 'Roots',
         'poisonous_potato': 'Poison Potato', 'armadillo_scute': 'Armadillo Scute'}
SYMBOL = {'raw_iron': 'Fe', 'raw_gold': 'Au', 'raw_copper': 'Cu', 'ancient_debris': 'Ad', 'diamond': 'Di', 'redstone': 'Rs',
          'coal': 'Co', 'lapis_lazuli': 'Lp', 'prismarine_shard': 'Ps', 'stone': 'St', 'sand': 'Sa', 'clay_ball': 'Cl',
          'tuff': 'Tf', 'cinnabar': 'Cn', 'netherrack': 'Nr', 'basalt': 'Ba', 'end_stone': 'Es', 'amethyst_shard': 'Am',
          'quartz': 'Qz', 'glowstone_dust': 'Gl', 'dirt': 'Dt', 'gravel': 'Gv', 'mud': 'Md', 'flint': 'Fl', 'obsidian': 'Ob',
          'soul_sand': 'Ss', 'crying_obsidian': 'Cy', 'emerald': 'Em', 'ice': 'Ic', 'snowball': 'Sn', 'pointed_dripstone': 'Dp',
          'sulfur_spike': 'S', 'froglight': 'Fg', 'log': 'Wo'}
TINT = {'short_grass': (124, 189, 107), 'vine': (89, 174, 48), 'lily_pad': (32, 128, 48)}
PLANTS = {'short_grass', 'vine', 'oak_sapling', 'red_mushroom', 'crimson_fungus', 'crimson_roots', 'tube_coral', 'tube_coral_fan',
          'spore_blossom', 'big_dripleaf', 'poppy', 'dandelion', 'orange_tulip', 'pink_tulip', 'allium', 'blue_orchid', 'azure_bluet',
          'lily_of_the_valley', 'cornflower', 'wither_rose', 'closed_eyeblossom', 'seagrass'}


def font(size):
    for path, index in (('/System/Library/Fonts/Helvetica.ttc', 1), ('C:/Windows/Fonts/arialbd.ttf', 0),
                        ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 0)):
        if Path(path).exists():
            return ImageFont.truetype(path, size, index=index)
    return ImageFont.truetype(BEBAS, size)


def square(p):
    im = Image.open(p).convert('RGBA')
    return im.crop((0, 0, im.width, im.width)) if im.height > im.width else im      # animated strips: first frame


def tint(im, rgb):
    r, g, b, a = im.split()
    r, g, b = (ch.point(lambda v, k=k: v * k // 255) for ch, k in zip((r, g, b), rgb))
    return Image.merge('RGBA', (r, g, b, a))


def iso(top, side, s):
    """A block drawn like an inventory icon: three faces, the sides shaded."""
    out = Image.new('RGBA', (s, s))
    T, S = (square(p).resize((64, 64), Image.Resampling.NEAREST) for p in (top, side))
    w, h = s / 2, s / 4

    def face(img, a, b, c, shade):
        (x0, y0), (x1, y1), (x2, y2) = a, b, c
        det = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        ia, ib, ic, id_ = (y2 - y0) / det, -(x2 - x0) / det, -(y1 - y0) / det, (x1 - x0) / det
        coeffs = (64 * ia, 64 * ib, -64 * (ia * x0 + ib * y0), 64 * ic, 64 * id_, -64 * (ic * x0 + id_ * y0))
        f = img.transform((s, s), Image.Transform.AFFINE, coeffs, resample=Image.Resampling.NEAREST)
        return tint(f, (int(255 * shade),) * 3) if shade < 1 else f
    out.alpha_composite(face(T, (0, h), (w, 0), (w, 2 * h), 1.0))
    out.alpha_composite(face(S, (0, h), (w, 2 * h), (0, 3 * h), .82))
    out.alpha_composite(face(S, (w, 2 * h), (2 * w, h), (w, 4 * h), .6))
    return out


def icon(cell, s):
    n = ICON.get(cell, cell)
    if (TEX / f'item/{n}.png').exists():
        im = square(TEX / f'item/{n}.png')
        return (tint(im, TINT[n]) if n in TINT else im).resize((s, s), Image.Resampling.NEAREST)
    if n == 'mob_head':
        return Image.open(TEX / 'entity/creeper/creeper.png').convert('RGBA').crop((8, 8, 16, 16)).resize((s, s), Image.Resampling.NEAREST)
    if n == 'big_dripleaf':
        return square(TEX / 'block/big_dripleaf_top.png').resize((s, s), Image.Resampling.NEAREST)
    side = next((f for f in (f'{n}_side', n, f'{n}_top', f'{n}_stage3', f'{n}_bottom') if (TEX / f'block/{f}.png').exists()), None)
    if side is None:
        return Image.new('RGBA', (s, s))
    top = next((f for f in (f'{n}_top', n, side) if (TEX / f'block/{f}.png').exists()), side)
    if n in PLANTS:
        im = square(TEX / f'block/{side}.png')
        return (tint(im, TINT[n]) if n in TINT else im).resize((s, s), Image.Resampling.NEAREST)
    return iso(TEX / f'block/{top}.png', TEX / f'block/{side}.png', s)


def symbols(cells):
    used, out = set(), {}
    for c in cells:
        nm = NAMES.get(c, c.replace('raw_', '').replace('_', ' ')).replace(' ', '')
        tries = ([SYMBOL[c]] if c in SYMBOL else []) + [nm[0].upper() + ch for ch in nm[1:].lower() if ch.isalpha()] + \
                [nm[0].upper() + ch for ch in 'abcdefghijklmnopqrstuvwxyz']
        out[c] = next(x for x in tries if x not in used)
        used.add(out[c])
    return out


def fit(text, width, size):
    while size > 10 and ImageFont.truetype(BEBAS, size).getlength(text) > width:
        size -= 2
    return ImageFont.truetype(BEBAS, size)


def tile(cell, size, colour, sym):
    t = Image.new('RGBA', (size, size))
    d = ImageDraw.Draw(t)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=max(4, size // 13), fill=colour + (255,), outline=(30, 30, 36, 255), width=max(2, size // 55))
    s = int(size * .46)
    t.alpha_composite(icon(cell, s), ((size - s) // 2, int(size * .27)))
    d.text((size * .94, 0), sym, font=font(int(size * .24)), fill=(25, 25, 30, 255), anchor='ra')
    nm = NAMES.get(cell, cell.replace('_', ' ').title())
    d.text((size // 2, size * .95), nm, font=font(int(size * (.12 if len(nm) < 12 else .09))), fill=(25, 25, 30, 255), anchor='md')
    return t


def main():
    g = json.load(open(ROOT / 'results/groups.json'))
    cols = {}
    for grp in g['groups']:
        key = 'Pairs' if grp['name'] == 'Pair' else grp['name']
        cols.setdefault(key, []).extend(grp['elements'])
    for k, order in ORDER.items():
        cols[k] = order + [e for e in cols[k] if e not in order]
    cols['Inert'] = g['inert']
    names = ['Tool-formers', 'Packers', 'Masonry', 'Colourants', 'Pairs', 'Inert']
    unplaced = g['no_group_yet']
    sym = symbols([c for n in names for c in cols[n]] + unplaced)

    ts, gap, ggap, rows, head, top, pad = 150, 10, 46, 10, 150, 330, 90
    W = pad * 2 + sum(WIDTH[n] * (ts + gap) for n in names) + ggap * (len(names) - 1)
    uts, ucols = 104, 17
    H = top + head + rows * (ts + gap) + 60 + 120 + ((len(unplaced) + ucols - 1) // ucols) * (uts + 8) + 60
    c = Image.new('RGBA', (W, H), (255, 255, 255, 255))
    d = ImageDraw.Draw(c)
    shadow, layer = Image.new('RGBA', (W, H)), Image.new('RGBA', (W, H))
    d.text((W // 2, 40), 'THE PERIODIC TABLE OF MINECRAFT', font=fit('THE PERIODIC TABLE OF MINECRAFT', W - 2 * pad, 200), fill=(21, 21, 21, 255), anchor='ma')
    sub = 'GROUPED THE WAY MENDELEEV DID IT: BY THE COMPOUNDS EACH ELEMENT FORMS'
    d.text((W // 2, 245), sub, font=fit(sub, W - 2 * pad, 58), fill=(90, 90, 96, 255), anchor='ma')
    x = pad
    for n in names:
        w = WIDTH[n] * (ts + gap) - gap
        d.rounded_rectangle([x, top, x + w, top + head - 26], radius=14, fill=COLOURS[n] + (255,), outline=(30, 30, 36, 255), width=3)
        d.text((x + w / 2, top + 14), n.upper(), font=fit(n.upper(), w - 16, 62), fill=(21, 21, 21, 255), anchor='ma')
        d.text((x + w / 2, top + 84), BLURBS[n], font=fit(BLURBS[n], w - 16, 30), fill=(60, 60, 66, 255), anchor='ma')
        for k, cell in enumerate(cols[n]):
            cx = x + (k % 2 if n == 'Pairs' else k // rows) * (ts + gap)
            cy = top + head + (k // 2 if n == 'Pairs' else k % rows) * (ts + gap)
            layer.alpha_composite(tile(cell, ts, COLOURS[n], sym[cell]), (cx, cy))
            shadow.paste((0, 0, 0, 80), (cx + 6, cy + 9, cx + ts + 6, cy + ts + 9))
        x += w + gap + ggap
    uy = top + head + rows * (ts + gap) + 60
    d.text((pad, uy), 'NO GROUP YET', font=ImageFont.truetype(BEBAS, 70), fill=(21, 21, 21, 255))
    d.text((pad + 330, uy + 22), 'FORM COMPOUNDS, BUT NOTHING ELSE FORMS THE SAME ONES', font=ImageFont.truetype(BEBAS, 40), fill=(90, 90, 96, 255))
    for k, cell in enumerate(unplaced):
        layer.alpha_composite(tile(cell, uts, COLOURS['No group yet'], sym[cell]), (pad + (k % ucols) * (uts + 8), uy + 100 + (k // ucols) * (uts + 8)))
    c.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(7)))
    c.alpha_composite(layer)
    c.convert('RGB').save(ROOT / 'table.png', optimize=True)
    print('table.png', c.size)


if __name__ == '__main__':
    main()
