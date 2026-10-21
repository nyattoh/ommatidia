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


def word_tokens(text):
    # Ignore layout and punctuation, while retaining every word and number.
    return re.findall(r"[^\W_]+(?:[’'][^\W_]+)*", text.casefold(), flags=re.UNICODE)


def source_word_tokens(markdown):
    tokens = []
    lists = []
    for token in MarkdownIt().parse(markdown):
        if token.type in ('ordered_list_open', 'bullet_list_open'):
            start = token.attrGet('start') or '1'
            lists.append([token.type, int(start)])
        elif token.type in ('ordered_list_close', 'bullet_list_close'):
            lists.pop()
        elif token.type == 'list_item_open' and lists and lists[-1][0] == 'ordered_list_open':
            tokens.append(str(lists[-1][1]))
            lists[-1][1] += 1
        elif token.type == 'inline':
            tokens.extend(word_tokens(token.content))
    return tokens


def corresponds(expected, actual):
    # PDF extraction can split one source token at a line wrap (notably URLs).
    source_index = pdf_index = 0
    while source_index < len(expected) and pdf_index < len(actual):
        if expected[source_index] == actual[pdf_index]:
            source_index += 1
            pdf_index += 1
            continue
        joined = actual[pdf_index]
        next_pdf_index = pdf_index + 1
        while len(joined) < len(expected[source_index]) and next_pdf_index < len(actual):
            joined += actual[next_pdf_index]
            next_pdf_index += 1
        if joined != expected[source_index]:
            return False
        source_index += 1
        pdf_index = next_pdf_index
    return source_index == len(expected) and pdf_index == len(actual)


# Exclude only the centred page-number footer; retain all other in-bounds text.
page_text = []
for i, page in enumerate(doc):
    text_blocks = []
    for block in page.get_text('blocks'):
        is_page_number = (
            block[1] >= page.rect.height-38
            and block[4].strip() == str(i+1)
            and abs((block[0]+block[2])/2-page.rect.width/2) <= 36
        )
        if not is_page_number:
            text_blocks.append(block[4])
    page_text.append('\n'.join(text_blocks))
alltext = '\n'.join(page_text)
blocks = [t.content for t in MarkdownIt().parse(source) if t.type == 'inline']
missing = [b[:100] for b in blocks if normal(b) not in normal(alltext)]
if not corresponds(source_word_tokens(source), word_tokens(alltext)):
    raise ValueError('PDF text does not correspond to the complete manuscript token sequence')
outside = []
for i, page in enumerate(doc):
    for b in page.get_text('blocks'):
        if b[0]<0 or b[1]<0 or b[2]>page.rect.width+1 or b[3]>page.rect.height+1:
            outside.append(i+1)
if missing:
    raise ValueError('PDF is missing manuscript text blocks: '+repr(missing))
if outside:
    raise ValueError('PDF text extends outside page bounds: '+repr(outside))
if '\ufffd' in alltext or '\x00' in alltext:
    raise ValueError('PDF contains replacement or null characters')
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
if 'Creative Commons Attribution 4.0 International (CC-BY-4.0)' not in metadata:
    raise ValueError('Zenodo metadata is missing the approved licence')
if 'https://creativecommons.org/licenses/by/4.0/' not in metadata:
    raise ValueError('Zenodo metadata is missing the licence URL')
if source.split('## Abstract\n\n')[1].split('\n\n## ')[0] not in metadata:
    raise ValueError('Zenodo metadata does not contain the manuscript abstract')
if '\npublished: false\n' not in (root/'articles/ommatidia-design-plan.md').read_text(encoding='utf-8'):
    raise ValueError('The Zenn article must remain unpublished')
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
(here/'validation.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
print(json.dumps(result))
