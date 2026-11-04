"""Build the student website and print sources from the reviewed course."""
import argparse,csv,hashlib,html,io,json,re,shutil,zipfile
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape
from PIL import Image

R=Path(__file__).resolve().parents[1];SITE=R/'site';DL=SITE/'downloads'
D=json.loads((R/'content/course.json').read_text(encoding='utf-8'))
BASE=D['meta']['site_url'];esc=lambda x:html.escape(str(x),quote=True)
FILES={x['name']:x['path'] for x in D['code_files']}
DOWNLOADS={x['name']:x for x in D['downloads']}
DOWNLOADS['Отчет о выполнении.docx']={'label':'Отчёт Word · ДКИП-4ХХпрог'}
DOWNLOADS['extended/Отчет о выполнении.docx']={'label':'Отчёт Word · VДКИП-31Хпрог и ДКИП-3ХХпрог'}
DL.mkdir(parents=True,exist_ok=True)

def code(b):
    if 'code' in b:return b['code']
    lines=(R/FILES[b['code_file']]).read_text(encoding='utf-8').splitlines()
    a,z=b.get('code_lines',[0,len(lines)]);return '\n'.join(lines[a:z])
def paras(value):return ''.join('<p>'+esc(p).replace('\n','<br>')+'</p>' for p in value.split('\n\n'))
def links(names):
    return '<div class="actions">'+''.join(f'<a class="button" href="downloads/{quote(n)}">{esc(DOWNLOADS.get(n,{}).get("label",n))}</a>' for n in dict.fromkeys(names))+'</div>'
def printlinks(names):
    return '<div class="file-links">'+''.join(f'<p><a href="{BASE}downloads/{quote(n)}">{esc(DOWNLOADS.get(n,{}).get("label",n))}</a><br><span>{esc(BASE+"downloads/"+n)}</span></p>' for n in dict.fromkeys(names))+'</div>'
def block(b,i,printing=False):
    if b['kind']=='image':
        p=R/b['path'];w,h=Image.open(p).size
        picture=f'<img width="{w}" height="{h}" src="assets/screenshots/{p.name}" alt="{esc(b.get("alt",b["title"]))}">'
        if b.get('crop'):
            x,y,cw,ch=b['crop'];assert 0<=x and 0<=y and x+cw<=w and y+ch<=h
            picture=f'<span class="screenshot-crop" style="aspect-ratio:{cw}/{ch}"><img src="assets/screenshots/{p.name}" alt="{esc(b.get("alt",b["title"]))}" style="width:{w/cw*100:.6f}%;left:{-x/cw*100:.6f}%;top:{-y/ch*100:.6f}%"></span>'
        return f'<li class="figure-row"><figure><a href="assets/screenshots/{p.name}">{picture}</a><figcaption>{esc(b["title"])}. {esc(b.get("text",""))}</figcaption></figure></li>'
    def card(title,body):
        check='<p class="result"><b>Проверка.</b> '+esc(b['check'])+'</p>' if b.get('check') else ''
        return f'<li class="step"><span class="number" aria-hidden="true">{i:02}</span><section class="card"><h3>{esc(title)}</h3>{body}{check}</section></li>'
    if b['kind']=='code':
        lines=code(b).splitlines()
        count=max(1,(len(lines)+27)//28);size=(len(lines)+count-1)//count
        chunks=[lines[n:n+size] for n in range(0,len(lines),size)] if printing else [lines]
        return ''.join(card(b['title']+(f' — часть {j+1} из {len(chunks)}' if len(chunks)>1 else ''),'<pre><code>'+esc('\n'.join(lines))+'</code></pre>') for j,lines in enumerate(chunks))
    parts=[];current=''
    for sentence in re.split(r'(?<=[.!?]) (?=[А-ЯA-Z0-9])',b.get('text','')):
        if len(current)+len(sentence)>1050 and current:parts.append(current);current=''
        current+=(' ' if current else '')+sentence
    if current:parts.append(current)
    return ''.join(card(b['title']+(' — продолжение' if j else ''),paras(p)) for j,p in enumerate(parts or ['']))
def chapter(s,label,anchor,printing=False):
    names=s.get('downloads',[])+[b['code_file'] for b in s['blocks'] if b.get('code_file')]
    rows=[];i=0
    for b in s['blocks']:
        if b['kind']!='image':i+=1
        rows.append(block(b,i,printing))
    return f'<article id="{anchor}" class="chapter"><header class="doc-head"><p class="section-id">{esc(label)}</p><h2>{esc(s["title"])}</h2></header><ol class="steps">'+''.join(rows)+'</ol>'+(printlinks(names) if printing else links(names))+'</article>'
NAV=[('index.html','Задание и файлы'),('lessons.html','Методика'),('areas.html','Предметные области'),('reference.html','Код образца')]
def page(title,body,active,printing=False):
    nav='' if printing else '<a class="skip" href="#main">К содержанию</a><nav aria-label="Материалы практики">'+''.join(f'<a href="{p}"'+(' aria-current="page"' if p==active else '')+'>'+n+'</a>' for p,n in NAV)+'</nav>'
    return '<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+' · ПП ПМ.04</title><link rel="stylesheet" href="assets/style.css"><link rel="icon" href="assets/favicon.svg"></head><body>'+nav+'<main id="main">'+body+'</main></body></html>'
def hero(title,lead):return '<div class="hero"><p class="section-id">Производственная практика ПМ.04</p><h1>'+esc(title)+'</h1><p>'+esc(lead)+'</p></div>'
def put(name,value):(SITE/name).write_text(value,encoding='utf-8')

def csvtext(rows):
    out=io.StringIO(newline='');csv.writer(out,delimiter=';',lineterminator='\n').writerows(rows);return out.getvalue()
def variant_archive(a):
    xx=f'{int(a["id"]):02}';subject=a['subject']
    raw=(R/f'stands/data/variant-{xx}.csv').read_text(encoding='utf-8-sig')
    good=list(csv.reader(io.StringIO(raw),delimiter=';'))[:3]
    control=list(csv.reader(io.StringIO((R/f'stands/data/variant-check-{xx}.csv').read_text(encoding='utf-8-sig')),delimiter=';'))
    order=[2,4,0,3,1];reordered=[[row[i] for i in order] for row in control]
    bad=[r.copy() for r in reordered];bad[0][1]='Due'
    middle=[r.copy() for r in reordered];middle[3]=middle[3][:3]
    inputs={f'variant-{xx}.csv':raw,f'variant-valid-{xx}.csv':csvtext(good),f'variant-check-{xx}.csv':csvtext(control),f'variant-reordered-{xx}.csv':csvtext(reordered),f'variant-bad-header-{xx}.csv':csvtext(bad),f'variant-middle-error-{xx}.csv':csvtext(middle)}
    instructions=f'Вариант {xx}. {subject}\n\n'+'\n\n'.join(b.get('text','') for b in a['blocks'])+'\n\nSource, Draft и будущая Work — соседние папки. Source не менять. BeforeFix и Delivery/v1.1 сохранить до исправлений.\nДанные:\n'+'\n'.join(inputs)+'\n\nОсновная методика: '+BASE+'lessons.html\nОтдельный тестовый проект: '+BASE+'downloads/ServiceDesk-fixed-example.zip\n'
    with zipfile.ZipFile(DL/f'variant-{xx}.zip','w',zipfile.ZIP_DEFLATED) as z:
        for folder,source in [('Source','ServiceDesk'),('Draft','ServiceDesk-csv-draft')]:
            for p in sorted((R/'stands'/source).iterdir()):
                if not p.is_file() or p.suffix not in {'.cs','.xaml','.csproj'}:continue
                value=p.read_text(encoding='utf-8')
                if p.name=='MainWindow.xaml':value=value.replace('Title="Сервисный журнал учебного центра"','Title="'+xml_escape(subject,{'"':'&quot;'})+'"')
                if p.name=='MainWindow.xaml.cs':
                    for old,new in [('Проектор',good[1][1]),('Ирина',good[1][2]),('Ноутбук',good[2][1]),('Павел',good[2][2])]:value=value.replace('"'+old+'"',json.dumps(new,ensure_ascii=False))
                z.writestr(folder+'/'+p.name,value.encode('utf-8'))
        for n,value in inputs.items():z.writestr('data/'+n,value.encode('utf-8'))
        z.writestr('START.html',('<!doctype html><html lang="ru"><meta charset="utf-8"><title>Стенд '+xx+'</title><body><pre style="white-space:pre-wrap;font:16px/1.6 sans-serif;max-width:800px;margin:40px auto">'+esc(instructions)+'</pre></body></html>').encode('utf-8'))

for d in D['downloads']:
    if d['kind']=='variant':variant_archive(next(a for a in D['areas'] if a['id']==d['variant']))
    elif d['kind']=='archive':
        with zipfile.ZipFile(DL/d['name'],'w',zipfile.ZIP_DEFLATED) as z:
            for name in d['files']:p=R/name;z.write(p,p.name)
    else:shutil.copyfile(R/d['path'],DL/d['name'])
for n,p in FILES.items():shutil.copyfile(R/p,DL/n)
for route,prefix in [('basic',''),('extended','extended/')]:
    target=DL/prefix/'Отчет о выполнении.docx';target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(R/'forms'/route/'Отчет о выполнении.docx',target)
legacy=DL/'report-template.md'
if legacy.exists():legacy.unlink()
shots=SITE/'assets/screenshots';shots.mkdir(parents=True,exist_ok=True)
for s in D['guide']:
    for b in s['blocks']:
        if b['kind']=='image':shutil.copyfile(R/b['path'],shots/Path(b['path']).name)

REPORTS=['Отчет о выполнении.docx','extended/Отчет о выполнении.docx']
COMMON=['ServiceDesk-source.zip','ServiceDesk-csv-draft.zip','ServiceDesk-fixed-example.zip','demo.csv','demo-valid.csv','demo-operator.csv','demo-reordered.csv','demo-bad-header.csv']+REPORTS
def assignment(printing=False):return ''.join(chapter(s,f'1.{i}. Задание',f'assignment-{i}',printing) for i,s in enumerate(D['assignment'],1))
def files(printing=False):return ''.join(chapter(s,'2. Файлы','files',printing) for s in D['files'])+(printlinks(COMMON) if printing else links(COMMON))
def guide(printing=False):return ''.join(chapter(s,f'3.{i}. Методика',f'step-{i}',printing) for i,s in enumerate(D['guide'],1))
def reference(printing=False):return ''.join(chapter(s,f'4.{i}. Полные файлы для сверки',f'ref-{i}',printing) for i,s in enumerate(D['reference'],1))
toc='<section class="contents"><h2>Порядок выполнения</h2><ol>'+''.join(f'<li><a href="#step-{i}">{esc(s["title"])}</a></li>' for i,s in enumerate(D['guide'],1))+'</ol></section>'
intro=hero('Сопровождение программного обеспечения','Настольный журнал своей области: диагностика, обмен CSV и передача обновления.')
put('index.html',page('Задание',intro+assignment()+files()+links(['assignment.pdf','guide.pdf']),'index.html'))
put('lessons.html',page('Методические рекомендации',intro+toc+guide()+links(REPORTS),'lessons.html'))
put('reference.html',page('Код образца',hero('Полные файлы для сверки','Исправленный образец объясняет способ. Обязательная работа выполняется в своей области.')+links(['ServiceDesk-fixed-example.zip'])+reference(),'reference.html'))
def areas(printing=False):
    out=chapter(dict(title='Как работать со своей областью',blocks=[D['area_completion']]),'Для всех вариантов','common',printing)
    for a in D['areas']:out+=chapter(a,f'Вариант {int(a["id"]):02}',f'variant-{a["id"]}',printing)
    return out
put('areas.html',page('Предметные области',hero('Предметные области','Выбрать назначенный номер и скачать его собственный стенд.')+links(['guide.pdf'])+areas(),'areas.html'))
put('print-method.html',page('Методические рекомендации',intro+assignment(True)+files(True)+guide(True)+reference(True),'',True))
put('print-areas.html',page('Предметные области',hero('Предметные области','Каждый вариант имеет свой проект, данные, правило и отдельную ссылку на стенд.')+areas(True),'',True))
def manifest():
    value={'title':D['meta']['title'],'files':{p.relative_to(SITE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SITE.rglob('*')) if p.is_file() and p.name!='manifest.json'}}
    (SITE/'manifest.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--skip-pdf',action='store_true');args=parser.parse_args()
    if not args.skip_pdf:
        import subprocess
        subprocess.run(['node',str(R/'tools/export_pdf.cjs')],check=True)
    manifest();print('Built site, 30 own stands, Word forms and print sources')
