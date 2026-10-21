"""Build the local English preprint and ignored Zenodo field worksheet."""
import hashlib
import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from markdown_it import MarkdownIt
from matplotlib import get_data_path
from reportlab.lib import colors
from reportlab.lib import fonts as reportlab_fonts
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'manuscript.md'
# The only (type, tag, markup) shapes the PDF renders, keyed by the enclosing token type.
RENDERED_SHAPES = {
    None: {('heading_open', 'h1', '#'), ('heading_open', 'h2', '##'), ('heading_open', 'h3', '###'),
           ('paragraph_open', 'p', ''), ('bullet_list_open', 'ul', '-'), ('ordered_list_open', 'ol', '.')},
    'bullet_list_open': {('list_item_open', 'li', '-')},
    'ordered_list_open': {('list_item_open', 'li', '.')},
    'list_item_open': {('paragraph_open', 'p', '')},
    'heading_open': {('inline', '', '')},
    'paragraph_open': {('inline', '', '')},
}


def unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('document-metadata.json contains a duplicate field')
        result[key] = value
    return result


def manuscript_tokens(text):
    """Parse the manuscript, rejecting every shape that the PDF would not render verbatim."""
    env = {}
    tokens = MarkdownIt().parse(text, env)
    if env.get('references'):
        raise ValueError('Unsupported manuscript markdown: link reference definition')
    stack = [[None, 0]]
    for token in tokens:
        if token.nesting < 0:
            opened, children = stack.pop()
            if opened in ('heading_open', 'paragraph_open', 'list_item_open') and children != 1:
                raise ValueError('Unsupported manuscript markdown: '+opened+' with '+str(children)+' blocks')
            continue
        stack[-1][1] += 1
        if (token.type, token.tag, token.markup) not in RENDERED_SHAPES[stack[-1][0]]:
            raise ValueError('Unsupported manuscript markdown at line '+str(token.map[0]+1)+': '+token.type)
        children = token.children or []
        if token.type == 'inline' and ([child.type for child in children] != ['text']
                                       or children[0].content != token.content):
            raise ValueError('Unsupported manuscript markdown at line '+str(token.map[0]+1)+': inline markup')
        if token.nesting > 0:
            stack.append([token.type, 0])
    return tokens


def zenodo_worksheet(title, affiliation, abstract):
    return f'''# Zenodo入力案 — 未投稿・著者確認用

画面の各項目へ以下を入力する案です。登録・公開操作は実施していません。

## Basic information → Resource type

Publication → Preprint

## Title

{title}

## Creators

Family name: Sakakibara
Given name: Ryoko
Affiliation: {affiliation}
ORCID: 0009-0009-9544-6315

既存の著者提供情報を転記。実名・ORCIDの公開はKota承認済み。

## Description

{abstract}

## Licenses → License

Creative Commons Attribution 4.0 International (CC-BY-4.0)
https://creativecommons.org/licenses/by/4.0/
論文・記事本文に適用。コードのライセンスは変更しない。

## Publication date

公開時にKotaが実際の日付を入力。

## Version

候補: 0.1.0-plan-draft。既存レコードの新バージョンにするか新規登録にするかをKotaが決めてから確定。

## Languages

English (eng)

## Keywords

large language models; investigation agents; evidence state; research protocol; system design; prospective evaluation

## Related works → relation / identifier / scheme

Cites / https://github.com/nyattoh/ommatidia / URL

## Files

manuscript.pdf, manuscript.md, SHA256SUMS.txt。必要に応じてpilot-estimate.mdも補足資料へ。
この入力案とZenn下書きは論文本文に混ぜない。

## Digital Object Identifier

既存の予約DOIの有無と対象レコードをKotaが確認。未確認のDOIは入力しない。

## Kotaが決めること

- 著者情報とCC-BY-4.0は承認済み。コードのライセンスは変更しない。
- 新規レコードか既存レコードの新バージョンか、予約DOI・版・公開日。
- PRレビュー後の公開可否とアップロードするファイル。
- Zenn記事の掲載可否。published: falseを維持中。
'''


if __name__ == '__main__':
    document_metadata = json.loads(
        (HERE/'document-metadata.json').read_text(encoding='utf-8'), object_pairs_hook=unique_json_object)
    approved_affiliation = 'Independent Researcher'
    if not isinstance(document_metadata, dict) or document_metadata.get('creatorAffiliation') != approved_affiliation:
        raise ValueError('document-metadata.json must contain the approved creator affiliation')
    epoch = os.environ.get('SOURCE_DATE_EPOCH')
    if epoch is None:
        epoch = str(int(datetime.fromisoformat(document_metadata['createdUtc'].replace('Z', '+00:00')).timestamp()))
    epoch = int(epoch)
    if epoch < 0:
        raise ValueError('SOURCE_DATE_EPOCH must be a non-negative integer')
    datetime.fromtimestamp(epoch, timezone.utc)
    text = SOURCE.read_text(encoding='utf-8')
    tokens = manuscript_tokens(text)
    lines = text.splitlines()
    headings = [
        (int(token.tag[1:]), tokens[index+1].content, token.map[0], token.map[1])
        for index, token in enumerate(tokens) if token.type == 'heading_open'
    ]
    titles = [heading for heading in headings if heading[0] == 1]
    abstracts = [heading for heading in headings if heading[:2] == (2, 'Abstract')]
    if len(titles) != 1 or len(abstracts) != 1:
        raise ValueError('Manuscript must contain one title and one Abstract section')
    title = titles[0][1]
    abstract_heading = abstracts[0]
    abstract_end = next((start for level, _, start, _ in headings
                         if level <= 2 and start > abstract_heading[2]), len(lines))
    abstract = '\n'.join(lines[abstract_heading[3]:abstract_end]).strip()
    fonts = Path(get_data_path()) / 'fonts/ttf'
    # ReportLab has no public unregister API, so restore its registries after this in-process build.
    registry_maps = (pdfmetrics._fonts, pdfmetrics._dynFaceNames,
                     reportlab_fonts._tt2ps_map, reportlab_fonts._ps2tt_map)
    registry_snapshots = tuple(registry.copy() for registry in registry_maps)
    try:
        font_names = ('OmmatidiaBody', 'OmmatidiaBold', 'OmmatidiaItalic')
        registered_fonts = [(name, TTFont(name, str(fonts / file))) for name, file in zip(font_names, (
            'DejaVuSerif.ttf', 'DejaVuSerif-Bold.ttf', 'DejaVuSerif-Italic.ttf'))]
        family = 'Ommatidia'
        for name, font in registered_fonts:
            pdfmetrics._fonts.pop(name, None)
            pdfmetrics._dynFaceNames.pop(font.face.name, None)
            reportlab_fonts._ps2tt_map.pop(name.lower(), None)
        for bold, italic in ((0, 0), (1, 0), (0, 1), (1, 1)):
            reportlab_fonts._tt2ps_map.pop((family.lower(), bold, italic), None)
        pdfmetrics.registerFontFamily(family, normal=font_names[0], bold=font_names[1],
                                      italic=font_names[2], boldItalic=font_names[1])
        for _, font in registered_fonts:
            pdfmetrics.registerFont(font)
        body = ParagraphStyle('Body', fontName=font_names[0], fontSize=9.2, leading=13.0, spaceAfter=6, splitLongWords=True)
        styles = {1: ParagraphStyle('Title', parent=body, fontName=font_names[1], fontSize=16, leading=20, spaceAfter=12),
                  2: ParagraphStyle('Section', parent=body, fontName=font_names[1], fontSize=11.2, leading=15, spaceBefore=9, keepWithNext=True),
                  3: ParagraphStyle('Subsection', parent=body, fontName=font_names[1], fontSize=10, leading=14, spaceBefore=6, keepWithNext=True)}
        story = []
        blocks = []
        list_stack = []
        for index, token in enumerate(tokens):
            if token.type == 'ordered_list_open': list_stack.append(int(token.attrGet('start') or 1))
            elif token.type == 'bullet_list_open': list_stack.append(None)
            elif token.type in ('ordered_list_close', 'bullet_list_close'): list_stack.pop()
            elif token.type == 'inline':
                previous = tokens[index-1]
                content = html.escape(token.content)
                style = styles.get(int(previous.tag[1:]), body) if previous.type == 'heading_open' else body
                bullet = None
                if previous.type == 'paragraph_open' and list_stack:
                    current = list_stack[-1]
                    bullet = '-' if current is None else str(current)+'.'
                    if current is not None: list_stack[-1] += 1
                    style = ParagraphStyle('Item', parent=body, leftIndent=13, firstLineIndent=0, bulletIndent=0)
                story.append(Paragraph(content, style, bulletText=bullet))
                blocks.append(token.content)

        def page_number(canvas, doc):
            canvas.saveState()
            canvas.setFont(font_names[0], 8)
            canvas.setFillColor(colors.HexColor('#555555'))
            canvas.drawCentredString(A4[0]/2, 25, str(doc.page))
            canvas.restoreState()

        def timestamped_canvas(*args, **kwargs):
            canvas = Canvas(*args, **kwargs)
            build_time = datetime.fromtimestamp(epoch, timezone.utc)
            canvas.setDateFormatter(lambda *_: "D:%04d%02d%02d%02d%02d%02d+00'00'" % (
                build_time.year, build_time.month, build_time.day,
                build_time.hour, build_time.minute, build_time.second))
            return canvas

        SimpleDocTemplate(str(HERE/'manuscript.pdf'), pagesize=A4, leftMargin=48, rightMargin=48,
            topMargin=45, bottomMargin=42, title=title, author='Ryoko Sakakibara', invariant=1,
            subject='Research plan and system design; zero comparative study trials').build(
                story, onFirstPage=page_number, onLaterPages=page_number, canvasmaker=timestamped_canvas)
    finally:
        for registry, snapshot in zip(registry_maps, registry_snapshots):
            registry.clear()
            registry.update(snapshot)

    metadata = zenodo_worksheet(title, document_metadata['creatorAffiliation'], abstract)
    (HERE/'zenodo-metadata.md').write_text(metadata, encoding='utf-8', newline='\n')
    paths = [SOURCE, HERE/'manuscript.pdf']
    (HERE/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in paths), encoding='utf-8', newline='\n')
    print(json.dumps({'sourceSha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'blocks':len(blocks), 'pdf':str(HERE/'manuscript.pdf'), 'licence':'CC-BY-4.0', 'sourceDateEpoch':epoch, 'studyTrialsRun':0}))
