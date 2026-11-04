"""Validate actual downloads, complete printed code, PDFs and report structure."""
import csv,hashlib,io,json,logging,re,zipfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
from lxml import etree
from pypdf import PdfReader
import pdfplumber
logging.getLogger('pdfminer').setLevel(logging.ERROR)
R=Path(__file__).resolve().parents[1];site=R/'site';dl=site/'downloads'
c=json.loads((R/'content/course.json').read_text(encoding='utf-8'))
assert len(c['areas'])==30 and len({a['id'] for a in c['areas']})==30
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.ids=set();self.codes=[];self.in_code=False
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if 'id' in d:assert d['id'] not in self.ids;self.ids.add(d['id'])
  for k in ['href','src']:
   if k in d:self.links.append(d[k])
  if tag=='code':self.in_code=True;self.codes.append('')
 def handle_endtag(self,tag):
  if tag=='code':self.in_code=False
 def handle_data(self,data):
  if self.in_code:self.codes[-1]+=data
pages={}
for p in site.glob('*.html'):
 parser=Links();parser.feed(p.read_text(encoding='utf-8'));pages[p.resolve()]=parser
for p,parser in pages.items():
 for link in parser.links:
  if re.match(r'^[a-zA-Z]+:',link):continue
  name,_,anchor=unquote(link).partition('#');target=(p.parent/name).resolve() if name else p
  assert target.exists(),(p.name,link)
  if anchor and target in pages:assert anchor in pages[target].ids,(p.name,link)
for d in c['downloads']:
 if d['kind']=='variant':continue
 if d['kind']=='archive':
  with zipfile.ZipFile(dl/d['name']) as z:
   assert set(z.namelist())=={Path(p).name for p in d['files']}
   for p in d['files']:assert z.read(Path(p).name)==(R/p).read_bytes(),p
 else:assert (dl/d['name']).read_bytes()==(R/d['path']).read_bytes()
for a in c['areas']:
 xx=f'{int(a["id"]):02}'
 with zipfile.ZipFile(dl/f'variant-{xx}.zip') as z:
  names=z.namelist();assert len(names)==17
  assert all(not n.startswith('/') and '..' not in Path(n).parts for n in names)
  for folder in ['Source','Draft']:
   assert sum(n.startswith(folder+'/') for n in names)==5
   assert a['subject'] in z.read(folder+'/MainWindow.xaml').decode('utf-8')
   etree.fromstring(z.read(folder+'/MainWindow.xaml'))
  def rows(name):return list(csv.reader(io.StringIO(z.read('data/'+name).decode('utf-8-sig')),delimiter=';'))
  partial=rows(f'variant-{xx}.csv');assert len(partial)==4 and len(partial[3])==3
  assert rows(f'variant-valid-{xx}.csv')==partial[:3]
  control=rows(f'variant-check-{xx}.csv');assert len(control)==7 and all(len(r)==5 for r in control)
  reordered=rows(f'variant-reordered-{xx}.csv');indices=[reordered[0].index(n) for n in control[0]]
  assert [[r[i] for i in indices] for r in reordered]==control
  middle=rows(f'variant-middle-error-{xx}.csv');assert len(middle)==7 and len(middle[3])==3 and sum(len(r)==5 for r in middle[1:])==5
  bad=rows(f'variant-bad-header-{xx}.csv');assert len(set(bad[0]))==4
print('PASS: all 30 self-contained stand archives and their six CSV inputs')
files={x['name']:x['path'] for x in c['code_files']};expected=[]
for s in c['guide']+c['reference']:
 for b in s['blocks']:
  if b['kind']!='code':continue
  if 'code' in b:value=b['code']
  else:
   lines=(R/files[b['code_file']]).read_text(encoding='utf-8').splitlines();a,z=b.get('code_lines',[0,len(lines)]);value='\n'.join(lines[a:z])
  expected.append(value)
assert '\n'.join(pages[(site/'print-method.html').resolve()].codes)=='\n'.join(expected)
for name in ['assignment','guide']:
 reader=PdfReader(dl/f'{name}.pdf');alltext='\n'.join(p.extract_text() for p in reader.pages)
 def outline_count(items):return sum(outline_count(x) if isinstance(x,list) else 1 for x in items)
 assert outline_count(reader.outline)>20
 with pdfplumber.open(dl/f'{name}.pdf') as doc:
  sizes=Counter();fonts=Counter()
  for i,p in enumerate(doc.pages):
   assert len(p.extract_text().strip())>6,(name,i+1,'empty')
   for ch in p.chars:
    assert ch['x0']>=83 and ch['x1']<=541 and ch['top']>=54 and ch['bottom']<=822,(name,i+1,ch)
    sizes[round(ch['size'],1)]+=1;fonts[ch['fontname']]+=1
  assert sizes[10.5]>5000 and sizes[8.0]>20,(name,sizes)
  assert all('Golos' in f for f in fonts if 'Consolas' not in f and 'Courier' not in f),fonts
  print(f'{name}.pdf: {len(doc.pages)} pages; actual 10.5 pt body / 8 pt footer, bounds and outlines passed')
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with zipfile.ZipFile(R/'forms/template/Отчет о выполнении.docx') as z:master={n:z.read(n) for n in z.namelist()}
for route,figures in [('basic',26),('extended',30)]:
 path=R/'forms'/route/'Отчет о выполнении.docx'
 assert (dl/('extended/' if route=='extended' else '')/'Отчет о выполнении.docx').read_bytes()==path.read_bytes()
 with zipfile.ZipFile(path) as z:
  for n,value in master.items():
   if n not in ['word/document.xml','docProps/core.xml']:assert z.read(n)==value,n
  xml=etree.fromstring(z.read('word/document.xml'))
  tags=xml.xpath('//w:sdtPr/w:tag/@w:val',namespaces=ns);assert len(tags)==len(set(tags))
  assert sum(t.startswith('pp04_figure_') for t in tags)==figures
  sections=c['report']['sections']+(c['report']['extended_sections'] if route=='extended' else [])
  labels=[label for section in sections for label in section['screenshots']]
  captions=xml.xpath('//w:p[.//w:instrText[contains(.,"SEQ Рисунок")]]',namespaces=ns)
  assert len(captions)==len(labels)==figures
  for number,(caption,label) in enumerate(zip(captions,labels),1):
   actual=''.join(caption.xpath('.//w:t/text()',namespaces=ns))
   assert actual==f'Рисунок {number} — '+label[:1].lower()+label[1:],actual
  for table in xml.xpath('//w:tbl[.//w:sdtPr/w:tag[starts-with(@w:val,"pp04_figure_")]]',namespaces=ns):
   height=table.xpath('.//w:trHeight',namespaces=ns)[0];assert height.get('{'+ns['w']+'}hRule','atLeast')=='atLeast' and int(height.get('{'+ns['w']+'}val'))>=3400
  assert 'Университет "Синергия"' in ''.join(xml.xpath('//w:t/text()',namespaces=ns))
 print('PASS:',route,'Word form, master fidelity, unique controls,',figures,'expandable figure slots')
m=json.loads((site/'manifest.json').read_text(encoding='utf-8'))
for p,digest in m['files'].items():assert hashlib.sha256((site/p).read_bytes()).hexdigest()==digest,p
print('PASS: complete printed fragments, internal links, downloaded forms and manifest')
