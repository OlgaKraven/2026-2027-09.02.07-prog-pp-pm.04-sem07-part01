"""Build the practice website, downloads and paginated PDFs from reviewed sources."""
import argparse,hashlib,html,json,os,re,shutil,textwrap,zipfile
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER,TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate,PageTemplate,Frame,Paragraph,Spacer,Table,TableStyle,KeepTogether,PageBreak,Image,Preformatted
from reportlab.platypus.tableofcontents import TableOfContents
from PIL import Image as PILImage

R=Path(__file__).resolve().parents[1]; SITE=R/'site'; DL=SITE/'downloads'
D=json.loads((R/'content/course.json').read_text(encoding='utf-8')); BASE=D['meta']['site_url']
esc=lambda x:html.escape(str(x),quote=True)
DL.mkdir(parents=True,exist_ok=True)
FILES={x['name']:x['path'] for x in D['code_files']}
DOWNLOADS={x['name']:x for x in D['downloads']}
def code(b):
    if 'code' in b:return b['code']
    lines=(R/FILES[b['code_file']]).read_text(encoding='utf-8').splitlines()
    a,z=b.get('code_lines',[0,len(lines)]);return '\n'.join(lines[a:z])
def paras(s):return ''.join('<p>'+esc(x).replace('\n','<br>')+'</p>' for x in s.split('\n\n'))
def actions(items):return '<div class="actions">'+''.join(f'<a class="button" href="{esc(p)}">{esc(n)}</a>' for p,n in items)+'</div>'
def download_links(names):return actions([('downloads/'+n,DOWNLOADS.get(n,{}).get('label',n)) for n in names])
def block(b,i):
    if b['kind']=='image':
        path=R/b['path']
        if not path.exists():raise FileNotFoundError(path)
        return f'<li class="figure-row"><figure><a href="assets/screenshots/{path.name}" aria-label="Открыть рисунок: {esc(b["title"])}"><img loading="lazy" width="{PILImage.open(path).width}" height="{PILImage.open(path).height}" src="assets/screenshots/{path.name}" alt="{esc(b.get("alt",b["title"]))}"></a><figcaption>{esc(b["title"])}. {esc(b.get("text",""))}</figcaption></figure></li>'
    body='<pre><code>'+esc(code(b))+'</code></pre>' if b['kind']=='code' else paras(b.get('text',''))
    check='<p class="result"><b>Проверка.</b> '+esc(b['check'])+'</p>' if b.get('check') else ''
    return f'<li class="step"><span class="number" aria-hidden="true">{i:02}</span><section class="card"><h3>{esc(b["title"])}</h3>{body}{check}</section></li>'
def chapter(s,num,anchor,method=False):
    return f'<article id="{anchor}" class="chapter'+(' method' if method else '')+f'"><header class="doc-head"><p class="section-id">{esc(num)}</p><h2>{esc(s["title"])}</h2></header><ol class="steps">'+''.join(block(b,i) for i,b in enumerate(s['blocks'],1))+'</ol>'+download_links(s.get('downloads',[]))+'</article>'
NAV=[('index.html','Задание и файлы'),('lessons.html','Методика'),('areas.html','Предметные области'),('reference.html','Код образца')]
def page(title,body,active):
    return '<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+' · ПП ПМ.04</title><link rel="stylesheet" href="assets/style.css"><link rel="icon" href="assets/favicon.svg"></head><body><a class="skip" href="#main">К содержанию</a><nav aria-label="Материалы практики">'+''.join(f'<a href="{p}"'+(' aria-current="page"' if p==active else '')+'>'+n+'</a>' for p,n in NAV)+'</nav><main id="main">'+body+'</main></body></html>'
def hero(title,lead):return '<div class="hero"><p class="section-id">Производственная практика ПМ.04</p><h1>'+esc(title)+'</h1><p>'+esc(lead)+'</p></div>'
def put(name,s):(SITE/name).write_text(s,encoding='utf-8')
LINKS=[('downloads/assignment.pdf','Методические рекомендации · PDF'),('downloads/guide.pdf','Предметные области · PDF'),('downloads/report-template.md','Шаблон отчёта')]
intro=hero('Сопровождение программного обеспечения','Настольный журнал своей предметной области: диагностика, обмен CSV и передача обновления.')
assignment=''.join(chapter(s,f'1.{i}. Задание',f'assignment-{i}') for i,s in enumerate(D['assignment'],1))
files=''.join(chapter(s,'2. Файлы для работы','files') for s in D['files'])
files+=download_links(['ServiceDesk-source.zip','ServiceDesk-csv-draft.zip','ServiceDesk-fixed-example.zip','demo.csv','demo-valid.csv','demo-operator.csv','demo-reordered.csv','demo-bad-header.csv'])+actions(LINKS)
put('index.html',page('Задание',intro+assignment+files+actions([('lessons.html','Перейти к методике'),('areas.html','Открыть назначенную область')]),'index.html'))
toc='<section class="contents"><h2>Порядок выполнения</h2><ol>'+''.join(f'<li><a href="#step-{i}">{esc(s["title"])}</a></li>' for i,s in enumerate(D['guide'],1))+'</ol></section>'
put('lessons.html',page('Методические рекомендации',hero('От исходного проекта к обновлению','Образец объясняет способ. Действия выполняются один раз в проекте назначенной области.')+actions(LINKS[:1])+toc+''.join(chapter(s,f'3.{i}. Методические рекомендации',f'step-{i}',True) for i,s in enumerate(D['guide'],1))+actions([('reference.html','Полные файлы для сверки'),('areas.html','Условие своего варианта')]),'lessons.html'))
areas=chapter(dict(title='Общий порядок проверки',blocks=[D['area_completion']]),'Для всех предметных областей','common')+actions([('index.html','Общее задание'),('lessons.html','Методика и подготовка сдачи')])
areas+='<section class="contents"><h2>Назначенная предметная область</h2><ol class="area-list">'+''.join(f'<li><a href="#variant-{a["id"]}">{esc(a["subject"])}</a></li>' for a in D['areas'])+'</ol></section>'
for a in D['areas']:
    areas+=chapter(dict(title=a['subject'],blocks=a['blocks']),f'Вариант {int(a["id"]):02}',f'variant-{a["id"]}')
    areas+=download_links(['ServiceDesk-source.zip','ServiceDesk-csv-draft.zip',f'variant-{int(a["id"]):02}.csv',f'variant-check-{int(a["id"]):02}.csv','ServiceDesk-fixed-example.zip'])
put('areas.html',page('Предметные области',hero('Предметные области','Сохранить назначенную область, её записи и особое условие отбора.')+actions(LINKS[1:2])+areas,'areas.html'))
put('reference.html',page('Код образца',hero('Полные файлы для сверки','Исходная и исправленная демонстрационные версии. Эти листинги доступны для чтения; их повторное переписывание не назначается.')+download_links(['ServiceDesk-source.zip','ServiceDesk-fixed-example.zip'])+''.join(chapter(s,f'Справочник {i}',f'ref-{i}') for i,s in enumerate(D['reference'],1)),'reference.html'))

SHOTS=SITE/'assets/screenshots';SHOTS.mkdir(parents=True,exist_ok=True)
for s in D['guide']:
    for b in s['blocks']:
        if b['kind']=='image':shutil.copyfile(R/b['path'],SHOTS/Path(b['path']).name)
for d in D['downloads']:
    if d['kind']=='archive':
        with zipfile.ZipFile(DL/d['name'],'w',zipfile.ZIP_DEFLATED) as z:
            for name in d['files']:
                p=R/name;z.write(p,p.name)
    else:shutil.copyfile(R/d['path'],DL/d['name'])
for name,path in FILES.items():shutil.copyfile(R/path,DL/name)
report='# Отчёт по производственной практике ПМ.04\n\n'
for i,s in enumerate(D['report']['sections'],1):report+=f'## {i}. {s["title"]}\n\n{s["prompt"]}\n\n'
(DL/'report-template.md').write_text(report.rstrip()+'\n',encoding='utf-8')

def fonts():
    system=Path(os.environ.get('PP04_TNR_DIR','C:/Windows/Fonts'))
    if (system/'times.ttf').exists():
        for name,f in [('Body','times.ttf'),('Bold','timesbd.ttf'),('Mono','consola.ttf')]:pdfmetrics.registerFont(TTFont(name,str(system/f)))
    else:
        font=SITE/'assets/fonts/GolosText-variable.ttf'
        for name in ['Body','Bold','Mono']:pdfmetrics.registerFont(TTFont(name,str(font)))
    pdfmetrics.registerFontFamily('Body',normal='Body',bold='Bold',italic='Body',boldItalic='Bold')
fonts()
W=160*mm
ST={
 'body':ParagraphStyle('body',fontName='Body',fontSize=14,leading=21,alignment=TA_JUSTIFY,firstLineIndent=12.5*mm,spaceAfter=8),
 'h1':ParagraphStyle('h1',fontName='Bold',fontSize=16,leading=24,alignment=TA_CENTER,textColor=colors.white,spaceAfter=2),
 'title':ParagraphStyle('title',fontName='Bold',fontSize=16,leading=24,alignment=TA_CENTER,spaceAfter=18),
 'h2':ParagraphStyle('h2',fontName='Bold',fontSize=14,leading=21,spaceAfter=10,keepWithNext=True),
 'caption':ParagraphStyle('caption',fontName='Body',fontSize=12,leading=14,alignment=TA_CENTER,spaceAfter=10),
 'toc':ParagraphStyle('toc',fontName='Body',fontSize=12,leading=17,spaceBefore=5),
 'code':ParagraphStyle('code',fontName='Mono',fontSize=10,leading=14),
 'link':ParagraphStyle('link',fontName='Body',fontSize=12,leading=17,spaceAfter=8,splitLongWords=True),
}
def para(s,style='body'):return Paragraph(esc(s).replace('\n','<br/>'),ST[style])
class PDF(BaseDocTemplate):
    def beforeDocument(self):
        self.context='';self.context_page=0
    def __init__(self,path,title):
        super().__init__(str(path),pagesize=A4,leftMargin=30*mm,rightMargin=20*mm,topMargin=20*mm,bottomMargin=20*mm,title=title,author='')
        frame=Frame(self.leftMargin,self.bottomMargin,self.width,self.height,id='body',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        self.context='';self.context_page=0
        self.addPageTemplates(PageTemplate('body',frame,onPage=self.footer,onPageEnd=self.running))
    def footer(self,canv,doc):
        canv.setFont('Body',10);canv.setFillColor(colors.black);canv.drawCentredString(A4[0]/2,10*mm,str(doc.page))
    def afterFlowable(self,f):
        if hasattr(f,'anchor'):
            self.canv.bookmarkPage(f.anchor);self.canv.addOutlineEntry(f.label,f.anchor,0,False)
            self.notify('TOCEntry',(0,f.label,self.page,f.anchor));self.context=f.label;self.context_page=self.page
    def running(self,canv,doc):
        if self.context and self.context_page!=self.page:
            title=self.context+' — продолжение'
            while pdfmetrics.stringWidth(title,'Body',10)>W:title=title[:-18]+'… — продолжение'
            canv.setFillColor(colors.black);canv.setFont('Body',10);canv.drawString(30*mm,A4[1]-14*mm,title)
def head(title,anchor):
    t=Table([[para(title,'h1')]],colWidths=[W]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#1c1c1c')),('LINEBELOW',(0,0),(-1,-1),3,colors.HexColor('#ed131c')),('LEFTPADDING',(0,0),(-1,-1),14),('RIGHTPADDING',(0,0),(-1,-1),14),('TOPPADDING',(0,0),(-1,-1),16),('BOTTOMPADDING',(0,0),(-1,-1),16)]));t.anchor=anchor;t.label=title;t.keepWithNext=True
    gap=Spacer(1,6*mm);gap.keepWithNext=True
    return [t,gap]
def chunks(s,limit=640):
    words=s.split();out=[];part=[];n=0
    for word in words:
        if n+len(word)>limit and part:out.append(' '.join(part));part=[];n=0
        part.append(word);n+=len(word)+1
    if part:out.append(' '.join(part))
    return out or ['']
def card(title,text):
    out=[]
    for j,chunk in enumerate(chunks(text)):
        content=[para(title+(' — продолжение' if j else ''),'h2'),para(chunk)]
        t=Table([[content]],colWidths=[W]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f4f4f6')),('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),10)]));out += [t,Spacer(1,5*mm)]
    return out
def pdfblocks(blocks):
    global FIG
    out=[]
    for i,b in enumerate(blocks,1):
        if b['kind']=='image':
            p=R/b['path'];im=PILImage.open(p);w=min(W,im.width);h=w*im.height/im.width
            if h>135*mm:w*=135*mm/h;h=135*mm
            FIG+=1
            out.append(KeepTogether([Image(str(p),w,h),para(f'Рисунок {FIG} — '+b['title'],'caption'),para(b.get('text',''))]))
        elif b['kind']=='code':
            lines=[]
            for line in code(b).splitlines():lines+=textwrap.wrap(line,width=78,replace_whitespace=False,drop_whitespace=False,break_long_words=True,break_on_hyphens=False) or ['']
            for off in range(0,len(lines),32):out += [para(f'{i}. '+b['title']+(' — продолжение' if off else ''),'h2'),Preformatted('\n'.join(lines[off:off+32]),ST['code']),Spacer(1,5*mm)]
        else:out+=card(f'{i}. '+b['title'],b.get('text','')+('\n\nПроверка. '+b['check'] if b.get('check') else ''))
    return out
def pdflinks(names,compact=False):
    out=[]
    for name in names:
        label=DOWNLOADS.get(name,{}).get('label',name);url=BASE+'downloads/'+name
        display=(('Контрольный CSV: ' if 'variant-check-' in name else 'Исходный CSV: ')+name) if compact else label+':<br/>'+esc(url)
        out.append(KeepTogether([Paragraph('<link href="'+esc(url)+'">'+display+'</link>',ST['link'])]))
    return out
def pdf(kind):
    global FIG;FIG=0
    method=kind=='method';filename='assignment.pdf' if method else 'guide.pdf'
    label='Методические рекомендации ПП ПМ.04' if method else 'Предметные области ПП ПМ.04'
    story=[para(label.upper(),'title'),para('Сопровождение настольного журнала. Диагностика, обмен CSV, обновление и откат.'),para('Сервисный журнал учебного центра — демонстрационный образец. Назначенная область и её данные сохраняются.'),PageBreak(),para('СОДЕРЖАНИЕ','title')]
    toc=TableOfContents();toc.levelStyles=[ST['toc']];story += [toc,PageBreak()]
    for i,s in enumerate(D['assignment'],1):story+=head(f'1.{i}. '+s['title'],f'assignment-{i}')+pdfblocks(s['blocks'])
    if method:
        story += [PageBreak()]
        for s in D['files']:story+=head('2. '+s['title'],'files')+pdfblocks(s['blocks'])
        story+=pdflinks(['ServiceDesk-source.zip','ServiceDesk-csv-draft.zip','ServiceDesk-fixed-example.zip','demo.csv','demo-valid.csv','demo-operator.csv','demo-reordered.csv','demo-bad-header.csv'])
        story.append(Paragraph('Шаблон отчёта:<br/><link href="'+BASE+'downloads/report-template.md">'+BASE+'downloads/report-template.md</link>',ST['link']))
        story+=[PageBreak()]
        for i,s in enumerate(D['guide'],1):story+=head(f'3.{i}. '+s['title'],f'step-{i}')+pdfblocks(s['blocks'])+pdflinks(s.get('downloads',[]))
        story += [PageBreak()]+head('4. Полные файлы для сверки','reference')+[para('Листинги сохранены для чтения. Исполняемый текст брать из файлов архива; печатные переносы длинной строки не переносить в код. Повторное переписывание полного образца не требуется.')]
        for i,s in enumerate(D['reference'],1):story+=head(f'4.{i}. '+s['title'],f'ref-{i}')+pdfblocks(s['blocks'])
    else:
        story += [para('Ссылки на файлы приведены под карточками. Те же загрузки доступны на странице предметных областей:'),Paragraph('<link href="'+BASE+'areas.html">'+BASE+'areas.html</link>',ST['link'])]
        for a in D['areas']:
            story += [PageBreak()]+head(f'Вариант {int(a["id"]):02}. '+a['subject'],f'variant-{a["id"]}')+pdfblocks(a['blocks'])+pdflinks([f'variant-{int(a["id"]):02}.csv',f'variant-check-{int(a["id"]):02}.csv'],compact=True)
    PDF(DL/filename,label).multiBuild(story)

if not argparse.ArgumentParser().parse_known_args()[1] or '--skip-pdf' not in os.sys.argv:
    pdf('method');pdf('areas')
manifest={'title':D['meta']['title'],'files':{p.relative_to(SITE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SITE.rglob('*')) if p.is_file() and p.name!='manifest.json'}}
(SITE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Built website, downloads and PDFs')
