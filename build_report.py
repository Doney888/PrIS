"""Build the IDEF0 report and standalone vector diagrams. Python + ReportLab.

The JSON file is the editable semantic model. No proprietary erwin format is claimed.
"""
from pathlib import Path
import json, math, html
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A3, landscape

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output'
ASSETS = ROOT / 'diagrams'
for d in (OUT, ASSETS):
    d.mkdir(exist_ok=True)
for name, file in [('Arial','arial.ttf'),('ArialB','arialbd.ttf'),('Times','times.ttf'),('TimesB','timesbd.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(Path('C:/Windows/Fonts') / file)))
pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='ArialB', italic='Arial', boldItalic='ArialB')
pdfmetrics.registerFontFamily('Times', normal='Times', bold='TimesB', italic='Times', boldItalic='TimesB')
PORTRAIT = A4
WIDE = landscape(A3)
PAGE = 0

def p(c, text, x, y, width, size=11, leading=None, font='Arial', align=0):
    """Paragraph positioned by its upper left corner, in page coordinates."""
    st = ParagraphStyle('p', fontName=font, fontSize=size, leading=leading or size*1.35,
                        alignment=align, splitLongWords=False)
    obj = Paragraph(text, st)
    _, h = obj.wrap(width, 2000)
    obj.drawOn(c, x, c._pagesize[1]-y-h)
    return y+h

def line(c, pts, arrow=False):
    h = c._pagesize[1]
    path = c.beginPath()
    path.moveTo(pts[0][0], h-pts[0][1])
    for x,y in pts[1:]:
        path.lineTo(x,h-y)
    c.drawPath(path)
    if arrow:
        x,y=pts[-1]; a,b=pts[-2]
        angle=math.atan2(y-b,x-a)
        q=c.beginPath(); q.moveTo(x,h-y)
        for da in (-.45,.45):
            xx=x-8*math.cos(angle+da); yy=y-8*math.sin(angle+da)
            q.lineTo(xx,h-yy)
        q.close(); c.drawPath(q,fill=1,stroke=0)

def rect(c,x,y,w,h):
    c.rect(x,c._pagesize[1]-y-h,w,h)

def label(c,text,x,y,w=120,size=10,align=0):
    st=ParagraphStyle('label',fontName='Arial',fontSize=size,leading=size*1.17,alignment=align,splitLongWords=False)
    z=Paragraph(html.escape(text),st); _,hh=z.wrap(w,500)
    c.saveState(); c.setFillColor(colors.white)
    c.rect(x-2,c._pagesize[1]-y-hh-1,w+4,hh+2,fill=1,stroke=0)
    c.setFillColor(colors.black);z.drawOn(c,x,c._pagesize[1]-y-hh);c.restoreState()
    return hh

def page_start(c, size=PORTRAIT, title=None):
    global PAGE
    PAGE+=1;c.setPageSize(size)
    c.setFillColor(colors.black);c.setStrokeColor(colors.black);c.setLineWidth(.65)
    if title:
        p(c,title,48,42,size[0]-96,16,20,'ArialB')
    c.setFont('Arial',8)
    c.drawString(48,23,'ПрИС | Лабораторная работа 3 | Команда 19')
    c.drawRightString(size[0]-48,23,str(PAGE))

def body(c,text,y=100):
    return p(c,text,48,y,PORTRAIT[0]-96,11.2,15.4,'Times')+12

def table(c, headers, rows, widths, y, size=9.5):
    style=ParagraphStyle('cell',fontName='Times',fontSize=size,leading=size*1.24)
    def para(t):return Paragraph(str(t),style)
    data=[[para('<b>'+s+'</b>') for s in headers]]+[[para(v) for v in row] for row in rows]
    t=Table(data,colWidths=widths,hAlign='LEFT')
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.45,colors.black),
                         ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eeeeee')),
                         ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
                         ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    _,hh=t.wrap(sum(widths),2000)
    assert y+hh<PORTRAIT[1]-50,(headers,y,hh)
    t.drawOn(c,48,PORTRAIT[1]-y-hh)
    return y+hh+14

def node(id,name):return {'id':id,'name':name}
def edge(source,target,name,route='forward',out_port=0,in_port=0):
    return dict(source=source,target=target,name=name,route=route,out_port=out_port,in_port=in_port)
def boundary(code,name,targets=None,source=None,route=None,port=0):
    r={'code':code,'name':name,'port':port}
    if targets is not None:r['targets']=targets
    if source is not None:r['source']=source
    if route:r['route']=route
    return r

ROOT_INPUTS=['Заявки игроков','Сведения о событиях партий','Замечания игроков']
ROOT_CONTROLS=['Правила игры и занятий','Порядок проверки, доступа и хранения']
ROOT_OUTPUTS=['Подтверждённые протоколы','Статистика и динамика игроков','Архив результатов']
ROOT_MECHANISM='Персонал и оборудование клуба'
NAMES=['Планировать занятие','Проводить занятие и регистрировать события','Проверять и подтверждать протокол',
       'Рассчитывать и публиковать статистику','Хранить и защищать результаты']

def make_model(state):
    to=state=='TO-BE'
    tools='Веб-ИС и резервное хранилище' if to else 'Чат, бумага и таблицы'
    main_nodes=[node('A'+str(i+1),n) for i,n in enumerate(NAMES)]
    root=node('A0','Организовывать тренировки и учитывать результаты')
    context=dict(state=state,id='A-0',title=root['name'],nodes=[root],edges=[],
        inputs=[boundary('I'+str(i+1),n,['A0']) for i,n in enumerate(ROOT_INPUTS)],
        controls=[boundary('C'+str(i+1),n,['A0']) for i,n in enumerate(ROOT_CONTROLS)],
        mechanisms=[boundary('M1',ROOT_MECHANISM,['A0']),boundary('M2',tools,['A0'])],
        outputs=[boundary('O'+str(i+1),n,source='A0') for i,n in enumerate(ROOT_OUTPUTS)],
        explanation=('Администратор собирает заявки в чате, тренер организует занятие, регистратор фиксирует события на бумаге. '
          'Результаты вручную переносятся в таблицу и согласуются с судьёй. Выходы показывают требуемые результаты деятельности; '
          'наличие выхода «Архив результатов» не означает надёжного резервирования.' if not to else
          'Граница деятельности сохраняется. Механизм M2 заменён веб-ИС с единым хранилищем и резервными копиями. '
          'Система поддерживает людей, но не судит партию и не оценивает отыгрыш. Подтверждение результата выполняет судья; '
          'внешний свод содержит только разрешённые данные.'))
    main=dict(state=state,id='A0',title=root['name'],nodes=main_nodes,
        inputs=[boundary('I1',ROOT_INPUTS[0],['A1']),boundary('I2',ROOT_INPUTS[1],['A2']),boundary('I3',ROOT_INPUTS[2],['A3'],port=1)],
        controls=[boundary('C1',ROOT_CONTROLS[0],['A1','A2','A3','A4']),boundary('C2',ROOT_CONTROLS[1],['A1','A3','A4','A5'])],
        mechanisms=[boundary('M1',ROOT_MECHANISM,[n['id'] for n in main_nodes]),boundary('M2',tools,[n['id'] for n in main_nodes])],
        outputs=[boundary('O1',ROOT_OUTPUTS[0],source='A3'),boundary('O2',ROOT_OUTPUTS[1],source='A4'),boundary('O3',ROOT_OUTPUTS[2],source='A5')],
        edges=[edge('A1','A2','План занятия','control'),edge('A2','A3','Рабочий протокол'),
               edge('A3','A4','Подтверждённый протокол'),edge('A4','A5','Комплект для архива'),
               edge('A3','A2','Запрос на исправление','feedback_top',out_port=1,in_port=1),
               edge('A5','A3','История результатов','feedback_bottom',out_port=1,in_port=2),
               edge('A5','A4','История результатов','feedback_bottom',out_port=1,in_port=1)],
        explanation=('Пять функций образуют общий цикл учёта. План A1 управляет проведением занятия A2. A3 сверяет бумажные записи, '
          'замечания и доступные старые файлы; при ошибке возвращает запрос в A2. A4 вручную готовит статистику и комплект для A5. '
          'История из A5 используется для проверки и сравнения, но собирается из отдельных файлов.' if not to else
          'Структура функций совпадает с AS-IS. В A2 события вводятся в ИС; в A3 техническая проверка дополняется подтверждением судьёй '
          'и сохранением ревизий. A4 формирует свод по подтверждённым данным. A5 хранит комплект, выполняет резервирование '
          'по регламенту и возвращает историю для проверки и анализа.'))
    a2names=(['Подготовить партии и участников','Организовать проведение партий','Записать события на бумаге','Перенести записи в таблицу'] if not to else
             ['Подготовить партии и участников','Организовать проведение партий','Внести события в ИС','Проверить структуру записей'])
    a2nodes=[node('A2'+str(i+1),n) for i,n in enumerate(a2names)]
    a2=dict(state=state,id='A2',title=NAMES[1],nodes=a2nodes,
        inputs=[boundary('I1','Сведения о событиях партий',['A23']),boundary('I2','Запрос на исправление',['A24'])],
        controls=[boundary('C1',ROOT_CONTROLS[0],['A21','A22','A23','A24']),boundary('C2','План занятия',['A21','A22'])],
        mechanisms=[boundary('M1',ROOT_MECHANISM,[n['id'] for n in a2nodes]),boundary('M2',tools,['A21','A23','A24'])],
        outputs=[boundary('O1','Рабочий протокол',source='A24')],
        edges=[edge('A21','A22','Состав партий'),edge('A22','A23','Сведения о партиях'),edge('A23','A24','Первичные записи'),
               edge('A24','A23','Уточнение записи','feedback_top',out_port=1,in_port=1)],
        explanation=('В A21 назначают пары и столы, в A22 организуют партии. A23 фиксирует наблюдаемые события на бумаге. '
          'В A24 записи повторно вводят в таблицу; обнаруженную неясность возвращают регистратору. Запрос из A3 также поступает в A24. '
          'На выходе остаётся рабочий, ещё не подтверждённый протокол.' if not to else
          'A21 и A22 выполняются людьми с поддержкой ИС. В A23 регистратор однократно вводит наблюдаемые события. '
          'A24 автоматически проверяет обязательные поля, допустимые значения и дубли; ошибки возвращаются в A23. '
          'Проверка структуры не доказывает достоверность события и не заменяет A3.'))
    a3names=(['Сверить протокол с источниками','Разобрать замечания','Согласовать исправленный протокол','Подтвердить результат вручную'] if not to else
             ['Сверить протокол с источниками','Разобрать замечания','Подготовить ревизию протокола','Подтвердить результат в ИС'])
    a3nodes=[node('A3'+str(i+1),n) for i,n in enumerate(a3names)]
    a3=dict(state=state,id='A3',title=NAMES[2],nodes=a3nodes,
        inputs=[boundary('I1','Рабочий протокол',['A31']),boundary('I2','Замечания игроков',['A32']),boundary('I3','История результатов',['A31'],port=1)],
        controls=[boundary('C1',ROOT_CONTROLS[0],['A31','A32','A33','A34']),boundary('C2',ROOT_CONTROLS[1],['A31','A32','A33','A34'])],
        mechanisms=[boundary('M1',ROOT_MECHANISM,[n['id'] for n in a3nodes]),boundary('M2',tools,[n['id'] for n in a3nodes])],
        outputs=[boundary('O1','Подтверждённые протоколы',source='A34'),boundary('O2','Запрос на исправление',source='A32',port=1)],
        edges=[edge('A31','A32','Протокол для проверки'),edge('A32','A33','Решение по замечаниям'),edge('A33','A34','Протокол на подтверждение'),
               edge('A34','A32','Отказ в подтверждении','feedback_top',out_port=1,in_port=1)],
        explanation=('Судья сопоставляет записи и доступную историю, разбирает замечания, согласует исправления и подтверждает результат '
          'сообщением или отметкой. Если исходные события нужно уточнить, A32 выдаёт запрос в A2. Правки таблицы не обеспечивают '
          'обязательного сохранения исходной версии, автора и причины; это недостаток AS-IS.' if not to else
          'Судья сверяет факты и разрешает замечания; ИС предоставляет историю. A33 готовит рабочую ревизию и предварительные показатели. '
          'При изменении подтверждённого результата сохраняются прежняя ревизия, автор, время и причина правки. A34 подтверждает новую '
          'ревизию; неподтверждённая версия не поступает в A4. При отказе протокол возвращается в A32.'))
    a4names=(['Отобрать подтверждённые результаты','Рассчитать показатели вручную','Собрать свод и историю игрока','Разослать свод и передать файлы'] if not to else
             ['Отобрать подтверждённые результаты','Рассчитать показатели в ИС','Сформировать свод и динамику','Опубликовать разрешённый свод'])
    a4nodes=[node('A4'+str(i+1),n) for i,n in enumerate(a4names)]
    a4=dict(state=state,id='A4',title=NAMES[3],nodes=a4nodes,
        inputs=[boundary('I1','Подтверждённые протоколы',['A41']),boundary('I2','История результатов',['A41'],port=1)],
        controls=[boundary('C1',ROOT_CONTROLS[0],['A41','A42','A43']),boundary('C2',ROOT_CONTROLS[1],['A41','A43','A44'])],
        mechanisms=[boundary('M1',ROOT_MECHANISM,[n['id'] for n in a4nodes]),boundary('M2',tools,[n['id'] for n in a4nodes])],
        outputs=[boundary('O1','Статистика и динамика игроков',source='A44'),boundary('O2','Комплект для архива',source='A44',port=1)],
        edges=[edge('A41','A42','Подтверждённая выборка'),edge('A42','A43','Рассчитанные показатели'),edge('A43','A44','Свод и протоколы')],
        explanation=('Ответственный выбирает согласованные результаты из файлов, вручную считает партии, победы и события, '
          'сопоставляет прошлые периоды. Свод пересылается в чат, протоколы и таблицы передаются на хранение в A5. '
          'Отдельная пересылка файлов создаёт задержку и риск публикации устаревшего результата.' if not to else
          'A41 выбирает актуальные подтверждённые ревизии. A42 рассчитывает число партий, побед и событий, A43 формирует свод, '
          'рейтинг и динамику с указанием числа партий. A44 проверяет права представления и публикует разрешённые данные. '
          'Комплект протоколов и сводов передаётся в A5; после повторного подтверждения исправления свод пересчитывается.'))
    return [context,main,a2,a3,a4]

def model():return {'project':'ПрИС, работа 3, команда 19','created':'2026-11-09',
 'format':'IDEF0 semantic model; not a native erwin project','diagrams':make_model('AS-IS')+make_model('TO-BE')}

def positions(d):
    if d['id']=='A-0':return {'A0':(445,330,300,130)}
    n=len(d['nodes']);gap=190 if n==5 else 245
    return {z['id']:(150+i*gap,240+i*(65 if n==5 else 75),150,76) for i,z in enumerate(d['nodes'])}

def draw_diagram(c,d,number):
    """A3 drawing sheet with a standard IDEF title area and explicit ICOM boundaries."""
    page_start(c,WIDE)
    W,H=WIDE
    p(c,f'{d["state"]} | {d["id"]}. {d["title"]}',35,26,W-70,17,21,'ArialB')
    rect(c,30,70,W-60,650)
    line(c,[(30,110),(W-30,110)])
    p(c,'AUTHOR: Команда 19',40,79,245,10)
    p(c,'DATE: 09.11.2026',300,79,185,10)
    p(c,'PROJECT: Бильярдный клуб',510,79,300,10)
    p(c,'STATUS: WORKING',935,79,200,10)
    pos=positions(d)
    iscontext=d['id']=='A-0'
    # Boundary inputs: dedicated approach channels keep input heads on left sides.
    for j,b in enumerate(d['inputs']):
        code=b['code']; target=b['targets'][0];x,y,w,h=pos[target]
        port=b.get('port',0)
        ty=y+h/2+(port*17-7 if port else -7)
        if iscontext:
            sy=347+j*42;ty=sy
            pts=[(55,sy),(x,ty)]
            labx,laby,labw=65,sy-22,310
        else:
            # Input lanes follow the staircase; multiple inputs to a box use distinct ports.
            sy=ty
            pts=[(55,sy),(x,ty)]
            labx,laby,labw=60,sy-21,min(290,x-75)
        line(c,pts,True)
        label(c,f'{code}  {b["name"]}' if iscontext else code,labx,laby,labw if iscontext else 38,10)
    # Controls enter from above. A branch dot distinguishes a junction from a crossing.
    for j,b in enumerate(d['controls']):
        yy=145+j*37
        txs=[]
        for target in b['targets']:
            x,y,w,h=pos[target];tx=x+34+j*75;txs.append(tx)
        line(c,[(min(txs),yy),(max(txs),yy)])
        line(c,[(min(txs),112),(min(txs),yy)])
        label(c,f'{b["code"]}  {b["name"]}',min(txs)+12,yy-23,420,10)
        for target,tx in zip(b['targets'],txs):
            x,y,w,h=pos[target]
            line(c,[(tx,yy),(tx,y)],True)
            if len(txs)>1:c.circle(tx,H-yy,2,fill=1,stroke=0)
    # Mechanisms use separate buses below the work boxes.
    for j,b in enumerate(d['mechanisms']):
        yy=648+j*35
        txs=[pos[t][0]+55+j*70 for t in b['targets']]
        line(c,[(min(txs),yy),(max(txs),yy)])
        line(c,[(min(txs),713),(min(txs),yy)])
        label(c,f'{b["code"]}  {b["name"]}',min(txs)+12,yy+5,470,10)
        for target,tx in zip(b['targets'],txs):
            x,y,w,h=pos[target]
            line(c,[(tx,yy),(tx,y+h)],True)
            if len(txs)>1:c.circle(tx,H-yy,2,fill=1,stroke=0)
    # Internal arrows: normal data, control from the plan, and explicit feedback loops.
    for e in d['edges']:
        sx,sy,sw,sh=pos[e['source']];tx,ty,tw,th=pos[e['target']]
        sp=e.get('out_port',0);ip=e.get('in_port',0)
        a=(sx+sw,sy+sh/2-7+sp*18)
        b=(tx,ty+th/2-7+ip*17)
        if e['route']=='control':
            # Plan is a constraint, entering the top of A2.
            by=ty-22;bx=tx+70
            pts=[a,(a[0]+22,a[1]),(a[0]+22,by),(bx,by),(bx,ty)]
            lx,ly,lw=a[0]+25,by-23,155
        elif e['route']=='feedback_top':
            yy=213
            pts=[a,(a[0]+15,a[1]),(a[0]+15,yy),(tx-22,yy),(tx-22,b[1]),b]
            lx,ly,lw=tx+10,yy-23,max(160,sx-tx)
        elif e['route']=='feedback_bottom':
            yy=618
            pts=[a,(a[0]+18,a[1]),(a[0]+18,yy),(tx-24,yy),(tx-24,b[1]),b]
            lx,ly,lw=tx+10,yy-22,180
        else:
            elbow=a[0]+22
            pts=[a,(elbow,a[1]),(elbow,b[1]),b]
            lx,ly,lw=sx+5,sy+sh+10,sw-10
        line(c,pts,True)
        label(c,e['name'],lx,ly,lw,9.5)
        if e['route']=='feedback_bottom':
            c.circle(tx-24,H-yy,2,fill=1,stroke=0)
    # Outputs use right-side source ports and explicit codes at the sheet boundary.
    for j,b in enumerate(d['outputs']):
        x,y,w,h=pos[b['source']];port=b.get('port',0)
        if iscontext:
            sy=350+j*42
            pts=[(x+w,sy),(W-55,sy)]
            lx,ly,lw=x+w+25,sy-23,W-x-w-90
        else:
            sy=y+h/2-7+port*18
            # For paired outputs from the last box, use one lower route to retain legible labels.
            if port:
                yy=592
                pts=[(x+w,sy),(x+w+35,sy),(x+w+35,yy),(W-55,yy)]
                lx,ly,lw=780,yy+5,320
            else:
                pts=[(x+w,sy),(W-55,sy)]
                lx,ly,lw=max(x+w+25,850),sy-23,min(265,W-max(x+w+25,850)-60)
                if lw<110:
                    lx=x+w+8;lw=W-60-lx
                    text=f'{b["code"]}  {b["name"]}'
                    st=ParagraphStyle('out',fontName='Arial',fontSize=9.5,leading=11.1)
                    _,hh=Paragraph(html.escape(text),st).wrap(lw,500)
                    ly=sy-hh-7
        line(c,pts,True);label(c,f'{b["code"]}  {b["name"]}',lx,ly,lw,9.5)
        for e in d['edges']:
            if e['source']==b['source'] and e.get('out_port',0)==b.get('port',0) and e['route']=='forward':
                c.circle(x+w+22,H-sy,2,fill=1,stroke=0)
    # Boxes are rendered last so crossing strokes never show through a function.
    for z in d['nodes']:
        x,y,w,h=pos[z['id']]
        c.setFillColor(colors.white);c.rect(x,H-y-h,w,h,fill=1,stroke=1);c.setFillColor(colors.black)
        p(c,html.escape(z['name']),x+9,y+14,w-18,11.5,14,align=1)
        c.setFont('Arial',10);c.drawRightString(x+w-8,H-y-h+7,z['id'])
    if not iscontext:
        label(c,'Входы: '+'; '.join(b['code']+' - '+b['name'] for b in d['inputs']),45,704,W-90,8.7)
    # Standard sheet title strip.
    rect(c,30,720,W-60,34)
    for xx in (175,W-155):line(c,[(xx,720),(xx,754)])
    p(c,'NODE: '+d['id'],40,730,125,11)
    p(c,'TITLE: '+d['title'],185,730,W-350,11)
    p(c,'NUMBER: '+str(number),W-145,730,110,11)
    p(c,d['explanation'],35,767,W-70,11.5,15,'Times')
    c.showPage()

def validate(m):
    """Check hierarchy, controls/results, endpoint coverage and parent-child balancing."""
    results=[]
    for state in ('AS-IS','TO-BE'):
        ds={d['id']:d for d in m['diagrams'] if d['state']==state}
        assert set(ds)=={'A-0','A0','A2','A3','A4'}
        parent=ds['A0']
        for d in ds.values():
            ids={n['id'] for n in d['nodes']}
            assert len(ids)==len(d['nodes'])
            assert len(ids)==1 if d['id']=='A-0' else 3<=len(ids)<=6
            controls=set();outputs=set()
            for b in d['controls']:controls.update(b['targets'])
            for b in d['outputs']:outputs.add(b['source'])
            for e in d['edges']:
                assert e['source'] in ids and e['target'] in ids
                outputs.add(e['source'])
                if e['route']=='control':controls.add(e['target'])
            assert ids<=controls,(state,d['id'],'missing control',ids-controls)
            assert ids<=outputs,(state,d['id'],'missing output',ids-outputs)
            for key in ('inputs','controls','mechanisms'):
                for b in d[key]:assert set(b['targets'])<=ids
            if d['id'] in ('A2','A3','A4'):
                id=d['id']
                # Derive the function interface from the actual parent graph, not a duplicate checklist.
                inherited={'inputs':[], 'controls':[], 'mechanisms':[], 'outputs':[]}
                for key in ('inputs','controls','mechanisms'):
                    for b in parent[key]:
                        if id in b['targets']:inherited[key].append(b['name'])
                for b in parent['outputs']:
                    if b['source']==id:inherited['outputs'].append(b['name'])
                for e in parent['edges']:
                    if e['target']==id:inherited['controls' if e['route']=='control' else 'inputs'].append(e['name'])
                    if e['source']==id:inherited['outputs'].append(e['name'])
                # Root boundary uses plural; inter-function arrows are a single party's protocol.
                def canon(s):return s.replace('Подтверждённый протокол','Подтверждённые протоколы')
                for key in inherited:
                    actual={canon(b['name']) for b in d[key]}
                    expected={canon(s) for s in inherited[key]}
                    assert actual==expected,(state,id,key,actual,expected)
            results.append(f'{state} {d["id"]}: endpoints, control/output coverage, block count OK')
        for key in ('inputs','controls','mechanisms','outputs'):
            assert {b['name'] for b in ds['A-0'][key]}=={b['name'] for b in parent[key]}
        results.append(f'{state}: A-0/A0 and A2/A3/A4 parent interfaces balanced')
    assert len(m['diagrams'])==10
    return results

def build(m):
    global PAGE
    PAGE=0
    report=OUT/'Laba_3_Komanda_19_Otchet.pdf'
    c=canvas.Canvas(str(report),pagesize=PORTRAIT,pageCompression=1)
    c.setTitle('Работа 3. Модели бизнес-процессов бильярдного клуба. Команда 19')
    c.setAuthor('Борисюк Е. Г.; Езиева Милана; Федорова Мария; Петрова Мария; Муравьев Матвей')
    page_start(c)
    p(c,'УНИВЕРСИТЕТ ИТМО',48,75,499,15,align=1,font='ArialB')
    p(c,'Проектирование информационных систем',48,116,499,13,align=1)
    p(c,'ЛАБОРАТОРНАЯ РАБОТА № 3',48,218,499,18,align=1,font='ArialB')
    p(c,'Разработка модели бизнес-процессов<br/>с учётом внедрения информационной системы',48,270,499,17,23,align=1)
    p(c,'Организация тренировок и учёт результатов<br/>любительского бильярдного клуба',48,354,499,14,20,align=1)
    p(c,'Команда № 19<br/><br/>Борисюк Е. Г., группа К3340<br/>Езиева Милана<br/>Федорова Мария<br/>Петрова Мария<br/>Муравьев Матвей',265,466,280,12,17)
    p(c,'Санкт-Петербург<br/>2026',48,741,499,11,16,align=1)
    c.showPage()
    page_start(c,title='1. Цель, исходные данные и границы')
    y=body(c,'<b>Цель работы</b> - описать деятельность клуба до и после внедрения выбранной ИС и определить, какие функции, '
       'информационные связи и способы выполнения работы изменятся.')
    y=body(c,'Основа - концепция C из лабораторной работы 2: собственное веб-приложение с единым интерфейсом занятий, событий, '
       'подтверждения и статистики. Рассматривается клуб по пулу-8. Масштаб учебной модели: 30 зарегистрированных игроков, '
       '5–10 участников занятия, 2 стола, 3 организатора и 60 занятий в год. Это допущения, а не результаты обследования.',y)
    y=body(c,'<b>Граница модели:</b> от получения заявки на занятие и наблюдаемых событий партий до выдачи подтверждённых '
       'протоколов, статистики и архива. Под занятием понимается тренировка клуба; внутри неё может быть несколько партий. '
       'Повторение регистрации и подтверждения для следующих партий не требует отдельной функции верхнего уровня.',y)
    y=table(c,['Участник','Ответственность'],[
        ['Администратор','Занятие, список участников, доступ, организация хранения и копий.'],
        ['Тренер','Пары, упражнения и оценка качества отыгрыша; анализ прогресса.'],
        ['Судья / регистратор','Наблюдение и ввод событий, разбор замечаний, подтверждение результата.'],
        ['Игрок','Заявка, участие, замечания и просмотр разрешённых результатов.'],
        ['Руководитель','Правила и порядок работы клуба. Роли могут совмещаться.']],[155,344],y)
    y=body(c,'В модель не включены платежи, бухгалтерия, видеораспознавание, официальные разряды и внешнее бронирование. '
       'Собственная система тренировочных баллов не вводится. ИС не принимает судейских решений.',y)
    body(c,'<b>Точка зрения:</b> организатор клуба. <b>Назначение модели:</b> сравнение способов организации и учёта; '
       'детальная схема БД и программные экраны в этой работе не проектируются.',y)
    c.showPage()
    page_start(c,title='2. Правила чтения и состав модели')
    y=body(c,'Модель выполнена в IDEF0. Оформление соответствует привычному виду листов erwin Process Modeler/BPwin: '
       'прямоугольные функции, ортогональные стрелки, номера узлов и рамка NODE / TITLE / NUMBER. Диаграммы являются '
       'векторными схемами; они не являются снимками экрана или файлом проекта erwin.')
    y=table(c,['Обозначение','Смысл и размещение'],[
        ['I - Input','Преобразуемые сведения; стрелка входит в левую сторону функции.'],
        ['C - Control','Правила и ограничения; стрелка входит сверху. План занятия также является управлением для A2.'],
        ['O - Output','Результат функции; стрелка выходит справа.'],
        ['M - Mechanism','Исполнители и средства; стрелка входит снизу. ИС - механизм деятельности, а не её управляющее правило.'],
        ['Номера','На A-0 показан блок A0; A0 раскрывает его в A1–A5. Диаграмма A2 раскрывает A2 в A21–A24.'],
        ['Ветвление и пересечение','Точка отмечает ветвление общей стрелки. Простое пересечение линий не означает обмена данными.']],[140,359],y)
    y=body(c,'IDEF0 показывает функциональные зависимости, а не точное время выполнения. Стрелка из A3 в A2 означает запрос '
       'на исправление, а не обязательный повтор всей тренировки. История из A5 - информационная обратная связь; '
       'для первого занятия она может быть пустой. Туннелированные стрелки не используются.',y)
    y=table(c,['Уровень','До внедрения','После внедрения'],[
        ['Контекст','A-0, лист 1','A-0, лист 6'],
        ['Первый уровень, 5 блоков','A0, лист 2','A0, лист 7'],
        ['Второй уровень, 4 блока','A2, лист 3','A2, лист 8'],
        ['Второй уровень, 4 блока','A3, лист 4','A3, лист 9'],
        ['Второй уровень, 4 блока','A4, лист 5','A4, лист 10']],[215,142,142],y)
    body(c,'Всего построено 10 диаграмм. Помимо обязательных двух блоков подробно раскрыт третий блок A4 в каждом состоянии. '
       'Номера листов в таблице соответствуют полю NUMBER на схемах, а не номеру страницы отчёта.',y)
    c.showPage()
    page_start(c,title='3. Словарь контекстных интерфейсов')
    y=table(c,['Код','Наименование','Содержание'],[
        ['I1',ROOT_INPUTS[0],'Запрос на участие, идентификатор игрока, доступность.'],
        ['I2',ROOT_INPUTS[1],'Наблюдаемые шары, фолы, отыгрыши и исход партии. Достоверность оценивает человек.'],
        ['I3',ROOT_INPUTS[2],'Сообщения о неточностях нового или уже опубликованного результата.'],
        ['C1',ROOT_CONTROLS[0],'Правила пула-8, порядок тренировки и правила расчёта показателей.'],
        ['C2',ROOT_CONTROLS[1],'Порядок подтверждения, исправления, доступа, хранения и резервирования. В AS-IS применяется вручную и непоследовательно.'],
        ['M1',ROOT_MECHANISM,'Администратор, тренер, судья/регистратор, игроки; столы, инвентарь, телефоны и ПК.'],
        ['M2','Средства учёта','AS-IS: чат, бумага и таблицы. TO-BE: веб-ИС, БД и резервное хранилище.'],
        ['O1',ROOT_OUTPUTS[0],'Проверенный судьёй результат; в TO-BE - конкретная подтверждённая ревизия.'],
        ['O2',ROOT_OUTPUTS[1],'Число партий, побед и событий; рейтинг и динамика по периоду с числом сыгранных партий.'],
        ['O3',ROOT_OUTPUTS[2],'Сохранённые протоколы и своды. В TO-BE - также история ревизий и копии по регламенту.']],[34,180,285],96)
    body(c,'Коды I/C/O/M на дочерних диаграммах нумеруются заново относительно раскрываемого блока. Например, I1 на A2 - '
       'сведения о событиях, а I1 на A3 - рабочий протокол. Их соответствие родителю проверяется по содержанию стрелок.',y)
    c.showPage()
    for i,d in enumerate(m['diagrams'],1):
        draw_diagram(c,d,i)
        # Each sheet is also available as an independent vector PDF.
        cc=canvas.Canvas(str(ASSETS/f'{d["state"]}_{d["id"]}.pdf'),pagesize=WIDE,pageCompression=1)
        old=PAGE;PAGE=0;draw_diagram(cc,d,i);PAGE=old;cc.save()
    page_start(c,title='4. Согласование уровней декомпозиции')
    y=body(c,'Внешние интерфейсы A-0 и A0 совпадают по содержанию в каждом состоянии. Детализация не добавляет '
       'новую деятельность за границами родительской функции. Ниже перечислены интерфейсы раскрытых блоков; '
       'состав одинаков для AS-IS и TO-BE, меняется способ выполнения.')
    y=table(c,['Узел','Входы / управления','Выходы'],[
        ['A2','I1: события партий; I2: запрос на исправление.<br/>C1: правила; C2: план занятия из A1.','O1: рабочий протокол в A3.'],
        ['A3','I1: рабочий протокол; I2: замечания; I3: история из A5.<br/>C1: правила; C2: порядок проверки, доступа и хранения.','O1: подтверждённый протокол в A4 и за границу A0;<br/>O2: запрос на исправление в A2.'],
        ['A4','I1: подтверждённые протоколы; I2: история из A5.<br/>C1: правила; C2: порядок проверки, доступа и хранения.','O1: статистика и динамика за границу A0;<br/>O2: комплект для архива в A5.']],[35,269,195],y)
    y=body(c,'M1 и M2 каждого раскрытого блока наследуются с A0. На нижнем уровне средства показываются только у тех '
       'подфункций, где они используются: например, бумажный протокол или ИС помогают учёту, но не выполняют сам удар.',y)
    y=body(c,'<b>Комплект для архива</b> содержит подтверждённый протокол и опубликованный свод. Его передача из A4 в A5 '
       'не означает, что данные до публикации вообще не сохранены: рабочие записи находятся в средствах учёта M2. '
       'A5 обеспечивает долговременное хранение и дальнейшее использование истории.',y)
    body(c,'<b>Замечание после публикации:</b> I3 поступает в A3, который получает прежний результат из A5. При необходимости '
       'уточнения событий выдаётся запрос в A2. После подготовки и повторного подтверждения результата A4 обновляет свод, '
       'A5 сохраняет новый комплект. В TO-BE исходная подтверждённая версия остаётся доступной в истории.',y)
    c.showPage()
    page_start(c,title='5. Различия процессов до и после внедрения')
    y=table(c,['Функция','AS-IS','TO-BE'],[
        ['A1. Планирование','Заявки в чате; администратор вручную составляет список и план.','Одно занятие и единый состав участников; администратор управляет записью в ИС.'],
        ['A2. Регистрация','Бумажная запись и повторный перенос в таблицу; уточнение почерка и пропусков.','Однократный ввод в ИС; проверка полей, значений и дублей; исправление ошибок ввода.'],
        ['A3. Подтверждение','Согласование вручную; правки файла не образуют обязательного журнала ревизий.','Решение судьи фиксируется; правка подтверждённого протокола создаёт ревизию с автором, временем и причиной.'],
        ['A4. Статистика','Ручной отбор, расчёт и пересылка; история собирается из файлов.','Расчёт из актуальных подтверждённых версий; рейтинг и динамика в едином интерфейсе.'],
        ['A5. Хранение','Разрозненные файлы и нерегулярные копии; восстановимость не проверяется.','Единый архив, роли доступа, резервирование и проверка восстановления по регламенту.']],[100,199,200],100)
    y=body(c,'Сохраняются правила игры, необходимость участия тренера и судьи, состав основных функций и бизнес-результаты. '
       'Изменяются механизмы и внутренние операции: повторный ввод сокращается, расчёт автоматизируется, '
       'подтверждение становится явным, а происхождение исправлений сохраняется.',y)
    body(c,'<b>Аварийный порядок:</b> при недоступности ИС регистратор временно ведёт бумажный протокол. После восстановления '
       'он переносит записи, сверяет дубли и направляет протокол на обычное подтверждение. Полноценная автономная '
       'синхронизация не предусматривается. Это исключительный способ выполнения A2, а не отдельный основной процесс.',y)
    c.showPage()
    page_start(c,title='6. Ожидаемый эффект и вывод')
    y=body(c,'Эффект следует из изменения операций, а не из самого наличия ИС. Исключение штатного переноса с бумаги '
       'уменьшает повторную работу A2; единый расчёт упрощает A4; ревизии делают проверяемой связь между A3 и A5. '
       'Точность регистрации по-прежнему зависит от ответственного человека.')
    y=table(c,['Показатель из работы 2','До внедрения','Целевое состояние'],[
        ['Административный труд на занятие','90 мин','25 мин для концепции C'],
        ['Срок доступности итога','До суток','До 5 мин после подтверждения'],
        ['Доступ и правки','Ручная организация работы с файлами','Только назначенные ответственные; исходная ревизия сохраняется'],
        ['Восстановление','Восстановимость не проверяется','RPO ≤24 ч; RTO ≤4 ч; контрольное восстановление']],[220,105,174],y)
    y=body(c,'Числа являются исходными гипотезами и целевыми требованиями концепции, а не результатом проведённого пилота. '
       'Снижение с 90 до 25 минут относится к административному труду, а не к длительности игры. По модели нельзя доказать '
       'фактическую экономию времени или окупаемость; это требует замеров. Новые экономические расчёты в задании 3 не требуются.',y)
    y=body(c,'Архивирование отдельного комплекта в A5 следует отличать от резервного копирования базы. Копии должны '
       'создаваться по расписанию и проверяться восстановлением. Показатели RPO и RTO описывают допустимую потерю '
       'данных и время восстановления и не обеспечиваются одной стрелкой «Архив».',y)
    body(c,'<b>Вывод.</b> Построены сопоставимые модели IDEF0 до и после внедрения: контекст, пять функций первого уровня '
       'и декомпозиции трёх функций для каждого состояния. Модель показывает, что ИС меняет организацию учёта, '
       'подтверждения, расчёта и хранения, сохраняя ответственность людей за наблюдение и судейские решения. '
       'Результат можно использовать для уточнения регламентов и требований следующей стадии проектирования.',y)
    c.showPage()
    page_start(c,title='Источники и проверка полноты задания')
    y=body(c,'1. Задание №3 «Разработка модели бизнес-процессов с учётом внедрения информационной системы». '
       'Материалы преподавателя, получены 09.11.2026.')
    y=body(c,'2. Команда 19. «Концепция информационной системы. Организация тренировок и учёт результатов любительского '
       'бильярдного клуба». Лабораторная работа 2, итоговый отчёт от 27.10.2026. '
       'Репозиторий: <link href="https://github.com/Doney888/PrIS/tree/lab02-concept">github.com/Doney888/PrIS/tree/lab02-concept</link>.',y)
    y=body(c,'3. NIST. Integration Definition for Function Modeling (IDEF0), FIPS PUB 183, 1993. '
       'Используется как описание нотации: ICOM, нумерация и декомпозиция, а не как действующее обязательное требование. '
       '<link href="https://nvlpubs.nist.gov/nistpubs/Legacy/FIPS/fipspub183.pdf">nvlpubs.nist.gov/nistpubs/Legacy/FIPS/fipspub183.pdf</link>.',y)
    y=body(c,'4. CA ERwin Model Navigator. User Guide, раздел «Navigating Process Models»: Activity Numbers, '
       'IDEF Title, Header/Footer Fields. '
       '<link href="https://ftpdocs.broadcom.com/cadocs/0/e003161e.pdf">ftpdocs.broadcom.com/cadocs/0/e003161e.pdf</link>. '
       'Дата обращения к источникам 3–4: 09.11.2026.',y)
    table(c,['Требование','Где выполнено'],[
        ['Контекст AS-IS и TO-BE','Листы диаграмм 1 и 6.'],
        ['Первый уровень, не менее 5 блоков','Листы 2 и 7: A1–A5.'],
        ['Декомпозиция не менее 2 блоков','A2 и A3 в обоих состояниях.'],
        ['Дополнительная декомпозиция','A4 в обоих состояниях; всего 3 раскрытых блока на состояние.'],
        ['Пояснения к каждой диаграмме','Под каждым листом 1–10.'],
        ['Основные различия','Разделы 5–6.'],
        ['Подкаст, дополнительное задание','Отдельный сценарий; для сдачи требуется записать аудио.']],[270,229],y)
    c.showPage();c.save()
    return report

if __name__=='__main__':
    path=ROOT/'model.json'
    if not path.exists():path.write_text(json.dumps(model(),ensure_ascii=False,indent=2),encoding='utf-8')
    m=json.loads(path.read_text(encoding='utf-8'))
    checks=validate(m)
    report=build(m)
    (ROOT/'VALIDATION.md').write_text('# Проверки модели\n\n'+'\n'.join('- '+r for r in checks)+'\n\nВсего: 10 диаграмм. Визуальная проверка выполняется отдельно.\n',encoding='utf-8')
    print(json.dumps({'report':str(report),'pages':PAGE,'checks':len(checks)},ensure_ascii=False))
