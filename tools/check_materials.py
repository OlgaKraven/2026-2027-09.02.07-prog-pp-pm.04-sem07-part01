"""Check internal links, packaged sources, variants and printable geometry."""
import json,re,zipfile,hashlib
from html.parser import HTMLParser
from pathlib import Path
import fitz

R=Path(__file__).resolve().parents[1];site=R/'site'
c=json.loads((R/'content/course.json').read_text(encoding='utf-8'))
assert len(c['areas'])==30 and len({a['id'] for a in c['areas']})==30
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.ids=set()
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if 'id' in d:assert d['id'] not in self.ids;self.ids.add(d['id'])
  for k in ['href','src']:
   if k in d:self.links.append(d[k])
pages={}
for p in site.glob('*.html'):
 parser=Links();parser.feed(p.read_text(encoding='utf-8'));pages[p.resolve()]=parser
for p,parser in pages.items():
 for link in parser.links:
  if re.match(r'^[a-zA-Z]+:',link):continue
  name,_,anchor=link.partition('#');target=(p.parent/name).resolve() if name else p
  assert target.exists(),(p.name,link)
  if anchor and target in pages:assert anchor in pages[target].ids,(p.name,link)
for d in c['downloads']:
 if d['kind']=='archive':
  with zipfile.ZipFile(site/'downloads'/d['name']) as z:
   assert set(z.namelist())=={Path(p).name for p in d['files']}
   for p in d['files']:assert z.read(Path(p).name)==(R/p).read_bytes(),p
 else:assert (site/'downloads'/d['name']).read_bytes()==(R/d['path']).read_bytes()
for name in ['assignment','guide']:
 doc=fitz.open(site/'downloads'/f'{name}.pdf')
 assert len(doc.get_toc())>20
 for i,p in enumerate(doc):
  assert len(p.get_text().strip())>6,(name,i+1,'empty')
  for b in p.get_text('blocks'):
   assert b[0]>=80 and b[2]<=540 and b[1]>=20 and b[3]<=830,(name,i+1,b[:4])
 assert 'продолжение' not in doc[0].get_text(),(name,'stale running heading on cover')
 print(f'{name}.pdf: {len(doc)} pages, geometry and outlines checked')
m=json.loads((site/'manifest.json').read_text(encoding='utf-8'))
for p,digest in m['files'].items():assert hashlib.sha256((site/p).read_bytes()).hexdigest()==digest,p
print('PASS: internal links, archives, 30 variants, PDFs and manifest')
