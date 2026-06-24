from pathlib import Path
import argparse
import re, textwrap

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description='Generate a Chinese PDF report from a Zhihu hot-list Markdown file.')
parser.add_argument('markdown', nargs='?', default=str(ROOT / 'reports' / 'zhihu_hot_top10_2026-06-23.md'), help='Markdown report path to convert.')
parser.add_argument('-o', '--output', help='Output PDF path. Defaults to the Markdown path with a .pdf suffix.')
args = parser.parse_args()
md_path = Path(args.markdown)
if not md_path.is_absolute():
    md_path = ROOT / md_path
pdf_path = Path(args.output) if args.output else md_path.with_suffix('.pdf')
if not pdf_path.is_absolute():
    pdf_path = ROOT / pdf_path
text = md_path.read_text(encoding='utf-8')
# Convert markdown table to readable bullets, strip table separators
lines=[]
for line in text.splitlines():
    if re.match(r'^\|\s*---', line):
        continue
    if line.startswith('|'):
        cells=[c.strip() for c in line.strip('|').split('|')]
        if cells and cells[0]=='排名':
            lines.append('排名｜热榜话题｜热度｜内容摘要')
        elif len(cells)>=4:
            lines.append(f"{cells[0]}. {cells[1]}（热度：{cells[2]}）")
            lines.append(f"   摘要：{cells[3]}")
        continue
    line=line.replace('# ','').replace('## ','').replace('**','')
    if line.strip(): lines.append(line)
    else: lines.append('')

# basic wrapping: Chinese chars count as 2-ish? use 43 unicode chars for A4 width
wrapped=[]
for line in lines:
    if not line:
        wrapped.append('')
    else:
        width = 34 if line.startswith('   ') else 38
        wrapped.extend(textwrap.wrap(line, width=width, break_long_words=True, replace_whitespace=False))

W,H=595,842
left=45; top=795; font_size=10.5; leading=15
pages=[]; cur=[]; y=top
for line in wrapped:
    if y < 45:
        pages.append(cur); cur=[]; y=top
    cur.append((line,y)); y-=leading if line else 10
if cur: pages.append(cur)

def pdf_hex(s): return s.encode('utf-16-be').hex().upper()
objects=[]
def add(obj):
    objects.append(obj); return len(objects)
# placeholders
catalog=add('')
pages_obj=add('')
font=add('''<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light /Encoding /UniGB-UCS2-H /DescendantFonts [ << /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light /CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 5 >> /FontDescriptor << /Type /FontDescriptor /FontName /STSong-Light /Flags 4 /Ascent 880 /Descent -120 /CapHeight 700 /StemV 80 >> >> ] >>''')
page_ids=[]
for pno,page in enumerate(pages,1):
    content=['BT', f'/F1 {font_size} Tf', f'{left} {top} Td']
    last_y=top
    for line,y in page:
        dy=y-last_y
        if dy: content.append(f'0 {dy} Td')
        if line:
            # use Tj hex string
            content.append(f'<{pdf_hex(line)}> Tj')
        last_y=y
    content.append('ET')
    stream='\n'.join(content).encode('utf-8')
    content_id=add(f'<< /Length {len(stream)} >>\nstream\n' + stream.decode('latin1') + '\nendstream')
    page_id=add(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] /Resources << /Font << /F1 {font} 0 R >> >> /Contents {content_id} 0 R >>')
    page_ids.append(page_id)
objects[catalog-1]='<< /Type /Catalog /Pages 2 0 R >>'
objects[pages_obj-1]=f'<< /Type /Pages /Kids [ ' + ' '.join(f'{i} 0 R' for i in page_ids) + f' ] /Count {len(page_ids)} >>'

out=bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
offsets=[0]
for i,obj in enumerate(objects,1):
    offsets.append(len(out))
    out.extend(f'{i} 0 obj\n'.encode())
    out.extend(obj.encode('latin1'))
    out.extend(b'\nendobj\n')
xref=len(out)
out.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
for off in offsets[1:]: out.extend(f'{off:010d} 00000 n \n'.encode())
out.extend(f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
pdf_path.write_bytes(out)
print(pdf_path)
print(f'pages={len(pages)} bytes={len(out)}')
