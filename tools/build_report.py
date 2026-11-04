"""Adapt copies of the retained common master to both PP PM.04 routes."""
from copy import deepcopy
from pathlib import Path
import hashlib,json,shutil,zipfile
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Mm
from docx.enum.table import WD_ROW_HEIGHT_RULE
import report_template_components as parts

R=Path(__file__).resolve().parents[1]
MASTER=R/'forms/template/Отчет о выполнении.docx'
SHA='5b91286458395ae589ded859021f287ce50cca1148cc5b29226b6fb1cb5373c4'
assert hashlib.sha256(MASTER.read_bytes()).hexdigest()==SHA
D=json.loads((R/'content/course.json').read_text(encoding='utf-8'))
def content_text(e):return ''.join(t.text or '' for t in e.iter(qn('w:t')))
def label_rows(table,labels,tag):
    original=deepcopy(table.rows[1]._tr)
    while len(table.rows)<len(labels)+1:table._tbl.append(deepcopy(original))
    while len(table.rows)>len(labels)+1:table._tbl.remove(table.rows[-1]._tr)
    for i,label in enumerate(labels,1):
        for j,cell in enumerate(table.rows[i].cells):
            controls=cell._tc.xpath('.//w:sdt')
            for k,c in enumerate(controls):
                c.find('w:sdtPr/w:tag',c.nsmap).set(qn('w:val'),f'{tag}_{i}_{j}_{k}')
                texts=list(c.find(qn('w:sdtContent')).iter(qn('w:t')))
                texts[0].text=label if j==0 else '____________'
                for t in texts[1:]:t.text=''
            if j==0 and not controls:
                texts=cell._tc.xpath('.//w:t');texts[0].text=label
                for t in texts[1:]:t.text=''
    for row in table.rows:
        row.height=Mm(12);row.height_rule=WD_ROW_HEIGHT_RULE.AT_LEAST

structure={}
for route in ['basic','extended']:
    out=R/'forms'/route/'Отчет о выполнении.docx';out.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(MASTER,out);doc=Document(out)
    for c in doc.element.xpath('.//w:sdt'):
        tag=c.find('w:sdtPr/w:tag',c.nsmap)
        if tag is not None and tag.get(qn('w:val'))=='practice_name':
            ts=list(c.find(qn('w:sdtContent')).iter(qn('w:t')))
            ts[0].text='Сопровождение и обслуживание программного обеспечения компьютерных систем (ПМ.04)'
            for t in ts[1:]:t.text=''
    label_rows(doc.tables[0],['Предметная область и вариант','Ссылка на свой ZIP-стенд','Основной и контрольный CSV','Назначенный маршрут группы'],'inputs')
    label_rows(doc.tables[1],['Windows','Visual Studio и WPF-компоненты','.NET SDK и Desktop Runtime','Редактор CSV и Microsoft Word'],'environment')
    label_rows(doc.tables[2],['Сервисный журнал учебного центра','Проектор / ноутбук; Ирина / Павел','demo.csv и demo-valid.csv','demo-operator.csv','Правило отбора демонстрации'],'mapping')
    labels=['Импорт и физические строки','Обратимость пяти полей','Контрольная дата и статусы','Правило своего варианта','Полный список и экспорт','Отрицательные примеры','Обновление и резервная копия','Настоящий откат']
    if route=='extended':labels+=['Обмен по именам и регрессия']
    label_rows(doc.tables[-1],labels,'final')
    # The source caption and mapping table stay together on their own page.
    doc.tables[2]._tbl.getprevious().get_or_add_pPr().append(parts.el('pageBreakBefore'))
    table=doc.tables[-1];table.autofit=False
    for col,w in zip(table.columns,[59,34,35,32]):col.width=Mm(w)
    for row in table.rows:
        row.height=Mm(10)
        for cell,w in zip(row.cells,[59,34,35,32]):cell.width=Mm(w)
    body=doc.element.body;children=list(body)
    start=next(i for i,e in enumerate(children) if content_text(e)=='Этап выполнения работы')
    end=next(i for i,e in enumerate(children) if content_text(e)=='Итоговая проверка и сдача')
    anchor=children[end]
    for e in children[start:end]:body.remove(e)
    stages=D['report']['sections']+(D['report']['extended_sections'] if route=='extended' else [])
    parts.CONTROL_ID=10000;fig=0
    for index,s in enumerate(stages,1):
        first=len(list(body))-1
        parts.heading(doc,s['title'],level=2,new_page=index>1)
        doc.add_paragraph(s['prompt'])
        parts.response(doc,'Исходные данные и ожидаемый результат',f's{index}_initial',2)
        parts.response(doc,'Выполненные действия',f's{index}_actions',3)
        parts.response(doc,'Фактический результат и проверка',f's{index}_actual',2)
        parts.response(doc,'Вывод по этапу и объяснение расхождений',f's{index}_conclusion',2)
        doc.add_page_break();p=doc.add_paragraph()
        p.add_run('Подтверждения этапа приведены на рис. ')
        for j,c in enumerate(s['screenshots']):
            if j:p.add_run(', ')
            parts.field(p,f'REF pp04_fig_{fig+j+1} \\h',str(fig+j+1))
        p.add_run('. Вставить собственные результаты, сохранив подписи.')
        for j,caption in enumerate(s['screenshots']):
            if j and j%2==0:doc.add_page_break()
            fig+=1;parts.figure_slot(doc,caption,f'pp04_figure_{fig}',fig,f'pp04_fig_{fig}')
        generated=list(body)[first:-1]
        for e in generated:body.remove(e);anchor.addprevious(e)
    for control_id,c in enumerate(doc.element.xpath('.//w:sdt'),30000):c.find('w:sdtPr/w:id',c.nsmap).set(qn('w:val'),str(control_id))
    doc.core_properties.title='Отчет о выполнении';doc.core_properties.subject='ПП ПМ.04'
    doc.core_properties.author=doc.core_properties.last_modified_by=''
    doc.core_properties.comments=doc.core_properties.keywords=''
    doc.save(out)
    with zipfile.ZipFile(out) as z:edited={n:z.read(n) for n in z.namelist()}
    with zipfile.ZipFile(MASTER) as z:original={n:z.read(n) for n in z.namelist()}
    allowed={'word/document.xml','docProps/core.xml'}
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for n,value in original.items():z.writestr(n,edited[n] if n in allowed else value)
    with zipfile.ZipFile(out) as z:
        for n,value in original.items():
            if n not in allowed:assert z.read(n)==value,n
    assert hashlib.sha256(MASTER.read_bytes()).hexdigest()==SHA
    structure[route]={'master_sha256':SHA,'main_sections':D['report']['main_sections'],'stages':stages,'figure_slots':fig}
    print(route,fig,'figure slots:',out)
(R/'content/report-structure.json').write_text(json.dumps(structure,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
