"""Step 3: do what Mendeleev did with the holes in his table.

Before the Copper Age update (Java 1.21.9, September 2025) copper had no tools, so the tool group had a hole between
stone and iron. Mendeleev filled his holes by averaging the elements on either side, so this does the same with
stone and iron, then compares the guess to the copper tools Mojang actually added.

The tool stats live in the game's ToolMaterial class. This reads the numbers straight out of it (no Java needed).

    python predict.py   ->  results/prediction.md
"""
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLASS = ROOT / 'game/net/minecraft/world/item/ToolMaterial.class'


def static_constants(path):
    """The constants the class's static initializer pushes, in order. Enough to read a table of materials."""
    b = path.read_bytes()
    count = struct.unpack('>H', b[8:10])[0]
    pool, i, k = [None], 10, 1
    while k < count:                                   # constant pool
        tag = b[i]; i += 1
        if tag == 1:
            n = struct.unpack('>H', b[i:i + 2])[0]; pool.append(('utf', b[i + 2:i + 2 + n].decode('utf8', 'replace'))); i += 2 + n
        elif tag in (3, 4):
            pool.append(('num', struct.unpack('>i' if tag == 3 else '>f', b[i:i + 4])[0])); i += 4
        elif tag in (5, 6):
            pool.append(('num', struct.unpack('>q' if tag == 5 else '>d', b[i:i + 8])[0])); pool.append(None); i += 8; k += 1
        elif tag in (7, 8, 16, 19, 20):
            pool.append((tag, struct.unpack('>H', b[i:i + 2])[0])); i += 2
        elif tag in (9, 10, 11, 12, 17, 18):
            pool.append((tag, struct.unpack('>HH', b[i:i + 4]))); i += 4
        elif tag == 15:
            pool.append((tag, b[i:i + 3])); i += 3
        else:
            raise ValueError(f'unknown constant tag {tag}')
        k += 1

    def utf(x):
        return pool[x][1]

    def name(ix):
        e = pool[ix]
        if e[0] in (9, 10, 11):
            cls, nt = e[1]
            return utf(pool[cls][1]).split('/')[-1] + '.' + utf(pool[nt][1][0])
        if e[0] == 8:
            return utf(e[1])
        if e[0] == 'num':
            return e[1]
        return str(e)
    i += 6
    i += 2 + 2 * struct.unpack('>H', b[i:i + 2])[0]   # interfaces

    def members(i):
        n = struct.unpack('>H', b[i:i + 2])[0]; i += 2; out = []
        for _ in range(n):
            _, nm, _, ac = struct.unpack('>HHHH', b[i:i + 8]); i += 8; attrs = []
            for _ in range(ac):
                an, al = struct.unpack('>HI', b[i:i + 6]); attrs.append((utf(an), b[i + 6:i + 6 + al])); i += 6 + al
            out.append((utf(nm), attrs))
        return i, out
    i, _ = members(i)
    i, methods = members(i)
    code = next(a for nm, attrs in methods if nm == '<clinit>' for an, a in attrs if an == 'Code')
    c = code[8:8 + struct.unpack('>I', code[4:8])[0]]
    width = {0x10: 1, 0x11: 2, 0x12: 1, 0x13: 2, 0x14: 2, 0xb2: 2, 0xb3: 2, 0xb4: 2, 0xb5: 2, 0xb6: 2, 0xb7: 2, 0xb8: 2,
             0xbb: 2, 0xbd: 2, 0xc0: 2, 0xba: 4, 0xb9: 4, 0x15: 1, 0x19: 1, 0x36: 1, 0x3a: 1, 0xbc: 1, 0x99: 2, 0x9a: 2,
             0xa7: 2, 0xc6: 2, 0xc7: 2, 0x84: 2}
    p, out = 0, []
    while p < len(c):
        op = c[p]
        if 0x02 <= op <= 0x08: out.append(op - 3)
        elif op in (0x0b, 0x0c, 0x0d): out.append(float(op - 0x0b))
        elif op == 0x10: out.append(struct.unpack('>b', c[p + 1:p + 2])[0])
        elif op == 0x11: out.append(struct.unpack('>h', c[p + 1:p + 3])[0])
        elif op == 0x12: out.append(name(c[p + 1]))
        elif op == 0xb3: out.append('PUT ' + str(name(struct.unpack('>H', c[p + 1:p + 3])[0])))
        p += 1 + width.get(op, 0)
    return out


def tool_materials():
    """{'STONE': {'durability': 131, 'speed': 4.0, 'damage': 1.0, 'enchantability': 5}, ...}"""
    out, nums = {}, []
    for x in static_constants(CLASS):
        if isinstance(x, str) and x.startswith('PUT ToolMaterial.'):
            if len(nums) >= 4:                         # each material is built from (durability, speed, damage, enchantability)
                durability, speed, damage, enchant = nums[-4:]
                out[x.split('.')[-1]] = {'durability': durability, 'speed': speed, 'damage': damage, 'enchantability': enchant}
            nums = []
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            nums.append(x)
    return out


def main():
    m = tool_materials()
    stone, iron, copper = m['STONE'], m['IRON'], m['COPPER']
    rows = [('Durability', 'durability'), ('Mining speed', 'speed'), ('Attack damage bonus', 'damage'), ('Enchantability', 'enchantability')]
    fmt = lambda v: f'{v:g}'
    lines = ['| Stat | Stone | Iron | Predicted (the average) | Real copper |', '|---|---|---|---|---|']
    for label, key in rows:
        guess = (stone[key] + iron[key]) / 2
        lines.append(f'| {label} | {fmt(stone[key])} | {fmt(iron[key])} | {fmt(guess)} | {fmt(copper[key])} |')
    table = '\n'.join(lines)
    (ROOT / 'results').mkdir(exist_ok=True)
    (ROOT / 'results/prediction.md').write_text('# Predicting copper tools\n\nStone and iron from the game\'s ToolMaterial class, averaged, next to the copper tools added in the Copper Age update.\n\n' + table + '\n')
    print(table)


if __name__ == '__main__':
    main()
