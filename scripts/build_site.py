"""Package the reviewed location maps into one static website."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'dist'
LOCATIONS = ('la', 'state-college')


def main():
    # Check inputs before replacing the disposable deployment directory.
    for slug in LOCATIONS:
        for name in ('index.html', 'rules.html', 'sw.js', 'manifest.webmanifest'):
            if not (ROOT / 'locations' / slug / 'map' / name).is_file():
                raise FileNotFoundError(f'Missing generated map: {slug}/{name}')
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    shutil.copytree(ROOT / 'site', OUTPUT)
    for slug in LOCATIONS:
        shutil.copytree(ROOT / 'locations' / slug / 'map', OUTPUT / slug)
    print('Built dist/: location picker, /la/, and /state-college/.')


if __name__ == '__main__':
    main()
