"""Check source/PDF correspondence, required hashes, licence and unpublished article."""
import hashlib
import json
import re
from pathlib import Path

import fitz
from markdown_it import MarkdownIt
from PIL import Image, ImageDraw
import yaml

here = Path(__file__).resolve().parent
root = here.parents[1]
source = (here/'manuscript.md').read_text(encoding='utf-8')
doc = fitz.open(here/'manuscript.pdf')
normal = lambda s: re.sub(r'\s+', '', s).replace('\u00ad', '')


class UniqueKeySafeLoader(yaml.SafeLoader):
    pass


def construct_unique_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as error:
            raise yaml.constructor.ConstructorError(
                'while constructing a mapping', node.start_mark,
                'found an unhashable key', key_node.start_mark,
            ) from error
        if duplicate:
            raise yaml.constructor.ConstructorError(
                'while constructing a mapping', node.start_mark,
                'found a duplicate key', key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping)


def unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('document-metadata.json contains a duplicate field')
        result[key] = value
    return result


def markdown_sections(markdown):
    lines = markdown.splitlines()
    tokens = MarkdownIt().parse(markdown)
    headings = []
    for index, token in enumerate(tokens):
        if token.type == 'heading_open':
            heading = tokens[index+1]
            headings.append((int(token.tag[1:]), heading.content, token.map[0], token.map[1]))
    sections = {}
    for index, (level, title, _, content_start) in enumerate(headings):
        content_end = len(lines)
        for next_level, _, next_start, _ in headings[index+1:]:
            if next_level <= level:
                content_end = next_start
                break
        sections.setdefault(title, []).append('\n'.join(lines[content_start:content_end]).strip())
    return sections


def required_section(sections, title):
    matches = sections.get(title, [])
    if len(matches) != 1:
        raise ValueError('Publication metadata must contain the '+title+' section exactly once')
    return matches[0]


def labelled_fields(section):
    fields = {}
    for line in section.splitlines():
        line = line.strip()
        if not line:
            continue
        if ':' not in line:
            continue
        label, value = (part.strip() for part in line.split(':', 1))
        if not label or label in fields:
            raise ValueError('Creator metadata contains an ambiguous labelled field')
        fields[label] = value
    return fields


def required_markdown_link(markdown, paragraph_prefix):
    matches = []
    for token in MarkdownIt().parse(markdown):
        if token.type != 'inline' or not token.content.startswith(paragraph_prefix):
            continue
        matches.append((token.content, token.children or []))
    if len(matches) != 1:
        raise ValueError('The publication licence declaration must appear exactly once')
    content, children = matches[0]
    links = []
    index = 0
    while index < len(children):
        if children[index].type == 'link_open':
            href = children[index].attrGet('href')
            label = []
            index += 1
            while index < len(children) and children[index].type != 'link_close':
                if children[index].type in ('text', 'code_inline', 'html_inline'):
                    label.append(children[index].content)
                index += 1
            links.append((''.join(label), href))
        index += 1
    if not links:
        return content, ''
    if len(links) != 1:
        raise ValueError('The publication licence declaration must contain one licence link')
    return links[0]


def article_published_false(article):
    lines = article.splitlines(keepends=True)
    if not lines or lines[0].rstrip('\r\n') != '---':
        return False
    closing = next((index for index, line in enumerate(lines[1:], 1)
                    if line.rstrip('\r\n') == '---'), None)
    if closing is None:
        return False
    try:
        frontmatter = yaml.load(''.join(lines[1:closing]), Loader=UniqueKeySafeLoader)
    except yaml.YAMLError:
        return False
    return isinstance(frontmatter, dict) and frontmatter.get('published') is False


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
metadata_sections = markdown_sections(metadata)
expected_title = source.splitlines()[0].removeprefix('# ')
if required_section(metadata_sections, 'Title') != expected_title:
    raise ValueError('Zenodo metadata is missing the approved title')
creator_fields = labelled_fields(required_section(metadata_sections, 'Creators'))
document_metadata = json.loads(
    (here/'document-metadata.json').read_text(encoding='utf-8'), object_pairs_hook=unique_json_object)
approved_affiliation = 'Independent Researcher'
if not isinstance(document_metadata, dict) or document_metadata.get('creatorAffiliation') != approved_affiliation:
    raise ValueError('document-metadata.json is missing the approved creator affiliation')
for label, approved, field in (
    ('Family name', 'Sakakibara', 'creator family name'),
    ('Given name', 'Ryoko', 'creator given name'),
    ('ORCID', '0009-0009-9544-6315', 'creator ORCID'),
    ('Affiliation', approved_affiliation, 'creator affiliation'),
):
    if creator_fields.get(label) != approved:
        raise ValueError('Zenodo metadata is missing the approved '+field)
if required_section(metadata_sections, 'Languages') != 'English (eng)':
    raise ValueError('Zenodo metadata is missing the approved language')
licence_lines = required_section(metadata_sections, 'Licenses → License').splitlines()
if 'Creative Commons Attribution 4.0 International (CC-BY-4.0)' not in licence_lines:
    raise ValueError('Zenodo metadata is missing the approved licence')
if 'https://creativecommons.org/licenses/by/4.0/' not in licence_lines:
    raise ValueError('Zenodo metadata is missing the licence URL')
abstract = required_section(markdown_sections(source), 'Abstract')
if required_section(metadata_sections, 'Description') != abstract:
    raise ValueError('Zenodo metadata does not contain the manuscript abstract')
article = (root/'articles/ommatidia-design-plan.md').read_text(encoding='utf-8')
article_licence_prefix = '\u8ad6\u6587\u3068\u3053\u306e\u8a18\u4e8b\u306e\u672c\u6587\u306f'
article_licence_name, article_licence_url = required_markdown_link(article, article_licence_prefix)
approved_article_licence_name = 'Creative Commons Attribution 4.0 International（CC-BY-4.0）'
if article_licence_name != approved_article_licence_name:
    if article_licence_url == '' and 'Creative Commons Attribution 4.0 International' in article_licence_name:
        raise ValueError('The article is missing the approved licence url')
    if 'Creative Commons Attribution 4.0 International' not in article_licence_name:
        raise ValueError('The article is missing the approved licence name')
    if 'CC-BY-4.0' not in article_licence_name:
        raise ValueError('The article is missing the approved licence identifier')
    raise ValueError('The article is missing the approved licence name')
if article_licence_url != 'https://creativecommons.org/licenses/by/4.0/':
    raise ValueError('The article is missing the approved licence url')
if not article_published_false(article):
    raise ValueError('The Zenn article frontmatter must contain published: false as a YAML boolean')
manuscript_licence_paragraphs = [
    token.content for token in MarkdownIt().parse(source)
    if token.type == 'inline' and 'Manuscript licence:' in token.content
]
if len(manuscript_licence_paragraphs) != 1:
    raise ValueError('The manuscript is missing the approved licence')
manuscript_licence = manuscript_licence_paragraphs[0].split('Manuscript licence:', 1)[1].strip()
if 'Creative Commons Attribution 4.0 International' not in manuscript_licence:
    raise ValueError('The manuscript is missing the approved licence name')
if 'CC-BY-4.0' not in manuscript_licence:
    raise ValueError('The manuscript is missing the approved licence identifier')
if 'https://creativecommons.org/licenses/by/4.0/' not in manuscript_licence:
    raise ValueError('The manuscript is missing the approved licence url')
if manuscript_licence != (
        'Creative Commons Attribution 4.0 International (CC-BY-4.0), '
        'https://creativecommons.org/licenses/by/4.0/.'):
    raise ValueError('The manuscript licence declaration is ambiguous')
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
