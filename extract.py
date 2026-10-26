"""Pull the files this project needs out of your own Minecraft client jar into ./game.

    python extract.py ~/.minecraft/versions/26.3/26.3.jar

Nothing from the game is included in this repo, so you need a copy of the game to run it.
"""
import sys
import zipfile
from pathlib import Path

KEEP = (
    'data/minecraft/recipe/',
    'data/minecraft/tags/item/',
    'data/minecraft/loot_table/',
    'assets/minecraft/textures/item/',
    'assets/minecraft/textures/block/',
    'assets/minecraft/textures/entity/creeper/',
    'net/minecraft/world/item/ToolMaterial.class',
)


def main():
    if len(sys.argv) != 2:
        sys.exit('usage: python extract.py <path to your Minecraft client .jar>')
    out = Path(__file__).resolve().parent / 'game'
    n = 0
    with zipfile.ZipFile(sys.argv[1]) as jar:
        for name in jar.namelist():
            if name.startswith(KEEP) and not name.endswith('/'):
                jar.extract(name, out)
                n += 1
    print(f'extracted {n} files into {out}')


if __name__ == '__main__':
    main()
