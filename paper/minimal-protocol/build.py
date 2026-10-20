"""Build the local English preprint and ignored Zenodo field worksheet."""
import hashlib
import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from markdown_it import MarkdownIt
from matplotlib import get_data_path
from reportlab.lib import colors
from reportlab import rl_config
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'manuscript.md'
document_metadata = json.loads((HERE/'document-metadata.json').read_text(encoding='utf-8'))
epoch = os.environ.get('SOURCE_DATE_EPOCH')
if epoch is None:
    epoch = str(int(datetime.fromisoformat(document_metadata['createdUtc'].replace('Z', '+00:00')).timestamp()))
epoch = int(epoch)
if epoch < 0:
    raise ValueError('SOURCE_DATE_EPOCH must be a non-negative integer')
datetime.fromtimestamp(epoch, timezone.utc)
rl_config.invariant = 1
text = SOURCE.read_text(encoding='utf-8')
title = text.splitlines()[0].removeprefix('# ')
abstract = text.split('## Abstract\n\n', 1)[1].split('\n\n## ', 1)[0].strip()
fonts = Path(get_data_path()) / 'fonts/ttf'
for name, file in [('Body', 'DejaVuSerif.ttf'), ('Bold', 'DejaVuSerif-Bold.ttf'), ('Italic', 'DejaVuSerif-Italic.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(fonts / file)))
pdfmetrics.registerFontFamily('Body', normal='Body', bold='Bold', italic='Italic', boldItalic='Bold')
body = ParagraphStyle('Body', fontName='Body', fontSize=9.2, leading=13.0, spaceAfter=6, splitLongWords=True)
styles = {1: ParagraphStyle('Title', parent=body, fontName='Bold', fontSize=16, leading=20, spaceAfter=12),
          2: ParagraphStyle('Section', parent=body, fontName='Bold', fontSize=11.2, leading=15, spaceBefore=9, keepWithNext=True),
          3: ParagraphStyle('Subsection', parent=body, fontName='Bold', fontSize=10, leading=14, spaceBefore=6, keepWithNext=True)}
tokens = MarkdownIt().parse(text)
story = []
blocks = []
list_stack = []
for index, token in enumerate(tokens):
    if token.type == 'ordered_list_open': list_stack.append(int(token.attrGet('start') or 1))
    elif token.type == 'bullet_list_open': list_stack.append(None)
    elif token.type in ('ordered_list_close', 'bullet_list_close'): list_stack.pop()
    elif token.type == 'inline':
        previous = tokens[index-1]
        content = html.escape(token.content).replace('\n', ' ')
        content = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', content)
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
    canvas.setFont('Body', 8)
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

metadata = f'''# Zenodo入力案 — 未投稿・著者確認用

画面の各項目へ以下を入力する案です。登録・公開操作は実施していません。

## Basic information → Resource type

Publication → Preprint

## Title

{title}

## Creators

Family name: Sakakibara
Given name: Ryoko
Affiliation: Independent Researcher
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
(HERE/'zenodo-metadata.md').write_text(metadata, encoding='utf-8', newline='\n')
paths = [SOURCE, HERE/'manuscript.pdf']
(HERE/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in paths), encoding='utf-8', newline='\n')
print(json.dumps({'sourceSha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'blocks':len(blocks), 'pdf':str(HERE/'manuscript.pdf'), 'licence':'CC-BY-4.0', 'sourceDateEpoch':epoch, 'studyTrialsRun':0}))
