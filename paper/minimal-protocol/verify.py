"""Check source/PDF correspondence, required hashes, licence and unpublished article."""
import hashlib
import json
import re
from pathlib import Path

import fitz
from markdown_it import MarkdownIt
from PIL import Image, ImageDraw

here = Path(__file__).resolve().parent
root = here.parents[1]
source = (here/'manuscript.md').read_text(encoding='utf-8')
doc = fitz.open(here/'manuscript.pdf')
normal = lambda s: re.sub(r'\s+', '', s).replace('\u00ad', '')
# Exclude page-number footers so cross-page paragraphs compare to source text.
alltext = '\n'.join(page.get_text(clip=fitz.Rect(0, 0, page.rect.width, page.rect.height-38)) for page in doc)
blocks = [t.content for t in MarkdownIt().parse(source) if t.type == 'inline']
missing = [b[:100] for b in blocks if normal(b) not in normal(alltext)]
outside = []
for i, page in enumerate(doc):
    for b in page.get_text('blocks'):
        if b[0]<0 or b[1]<0 or b[2]>page.rect.width+1 or b[3]>page.rect.height+1:
            outside.append(i+1)
assert not missing, missing
assert not outside, outside
assert '\ufffd' not in alltext and '\x00' not in alltext
expected = {'manuscript.md', 'manuscript.pdf'}
entries = {}
for line in (here/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
    match = re.fullmatch(r'([0-9a-f]{64})  (manuscript\.md|manuscript\.pdf)', line)
    if match is None:
        raise ValueError('Malformed or unexpected SHA256SUMS.txt entry')
    digest, name = match.groups()
    if name in entries:
        raise ValueError('Duplicate SHA256SUMS.txt entry: '+name)
    entries[name] = digest
if set(entries) != expected:
    raise ValueError('SHA256SUMS.txt must contain manuscript.md and manuscript.pdf exactly once')
for name, digest in entries.items():
    if hashlib.sha256((here/name).read_bytes()).hexdigest() != digest:
        raise ValueError('SHA256 mismatch: '+name)
metadata = (here/'zenodo-metadata.md').read_text(encoding='utf-8')
assert 'Creative Commons Attribution 4.0 International (CC-BY-4.0)' in metadata
assert 'https://creativecommons.org/licenses/by/4.0/' in metadata
assert source.split('## Abstract\n\n')[1].split('\n\n## ')[0] in metadata
assert '\npublished: false\n' in (root/'articles/ommatidia-design-plan.md').read_text(encoding='utf-8')
render = here/'rendered'
render.mkdir(exist_ok=True)
thumbs = []
for i, page in enumerate(doc):
    pix = page.get_pixmap(matrix=fitz.Matrix(1.1, 1.1))
    pix.save(render/f'page-{i+1}.png')
    img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
    img.thumbnail((420, 594))
    tile = Image.new('RGB', (440, 625), '#dddddd')
    tile.paste(img, (10, 20))
    ImageDraw.Draw(tile).text((10, 3), str(i+1), fill='black')
    thumbs.append(tile)
canvas = Image.new('RGB', (880, 625*((len(thumbs)+1)//2)), '#dddddd')
for i, img in enumerate(thumbs):
    canvas.paste(img, ((i%2)*440, (i//2)*625))
canvas.save(render/'contact.png')
result = dict(pages=len(doc), sourceBlocksChecked=len(blocks), missingBlocks=missing,
    outsidePageBlocks=outside, replacementGlyphs=0, checksums='pass', licenceField='CC-BY-4.0',
    zennPublished=False, comparativeTrialsRun=0, wordCount=len(source.split()),
    sourceSha256=hashlib.sha256((here/'manuscript.md').read_bytes()).hexdigest(),
    pdfSha256=hashlib.sha256((here/'manuscript.pdf').read_bytes()).hexdigest(),
    sourceBaseline='b8cc565ef016f531fdef7325801e3468db82135f')
(here/'validation.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result))
