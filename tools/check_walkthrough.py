"""Compile the actual printed fragments in the order assigned to students."""
import json,re,shutil,subprocess,zipfile,uuid
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=json.loads((R/'content/course.json').read_text(encoding='utf-8'))
FILES={x['name']:x['path'] for x in D['code_files']}
W=R/'.work'/('walkthrough-'+uuid.uuid4().hex[:8]);W.mkdir(parents=True,exist_ok=True)
def code(b):
    if 'code' in b:return b['code']
    lines=(R/FILES[b['code_file']]).read_text(encoding='utf-8').splitlines();a,z=b.get('code_lines',[0,len(lines)]);return '\n'.join(lines[a:z])
def codes(stage):return [code(b) for b in D['guide'][stage-1]['blocks'] if b['kind']=='code']
def replace_method(text,signature,replacement):
    start=text.index(signature);body=text.index('{',start);end=body+1;depth=1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[:start]+replacement+text[end:]
def build(label):
    result=subprocess.run(['dotnet','build',str(W/'ServiceDesk.csproj'),'-v:q','--nologo'],text=True,capture_output=True)
    if result.returncode:raise AssertionError(label+'\n'+result.stdout+'\n'+result.stderr)
    print('PASS:',label)
def illustration_checkpoint(name):
    target=R/'.work'/name;target.mkdir(exist_ok=True)
    for filename in ['ServiceDesk.csproj','App.xaml','App.xaml.cs','MainWindow.xaml','MainWindow.xaml.cs']:
        value=(W/filename).read_text(encoding='utf-8')
        if filename=='MainWindow.xaml':value=value.replace('Title="Библиотечные выдачи"','Title="Сервисный журнал учебного центра"')
        (target/filename).write_text(value,encoding='utf-8')
    result=subprocess.run(['dotnet','build',str(target/'ServiceDesk.csproj'),'-v:q','--nologo'],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
with zipfile.ZipFile(R/'site/downloads/variant-01.zip') as z:
    for n in z.namelist():
        if n.startswith('Source/'):target=W/Path(n).name;target.write_bytes(z.read(n))
build('own area base, before CSV')
with zipfile.ZipFile(R/'site/downloads/variant-01.zip') as z:
    for name in ['App.xaml.cs','MainWindow.xaml','MainWindow.xaml.cs']:(W/name).write_bytes(z.read('Draft/'+name))
build('coordinated Draft transfer')
main=(W/'MainWindow.xaml.cs').read_text(encoding='utf-8')
record,read,load,app=codes(6)
pos=main.index('\n',main.index('internal record Ticket'))+1;main=main[:pos]+record+'\n'+main[pos:]
main=replace_method(main,'    public static List<Ticket> Read(string path)',read)
main=replace_method(main,'    private void LoadCsv(string path)',load)
(W/'MainWindow.xaml.cs').write_text(main,encoding='utf-8');(W/'App.xaml.cs').write_text(app,encoding='utf-8')
build('D1, all coordinated printed replacements, before D2')
illustration_checkpoint('method-d1')
main=replace_method(main,'    public static void Write(string path, IEnumerable<Ticket> rows)',codes(7)[0])
(W/'MainWindow.xaml.cs').write_text(main,encoding='utf-8');build('D2, printed writer')
pos=main.index('internal static class CsvStore');head,tail=main[:pos],main[pos:]
old='    public static int CountOverdue(IEnumerable<Ticket> rows, DateTime today) =>\n        rows.Count(t => t.Due.Date < today.Date);'
assert old in tail;main=head+tail.replace(old,codes(8)[0],1)
(W/'MainWindow.xaml.cs').write_text(main,encoding='utf-8');build('D3, printed overdue rule')
operator,handlers,buttons=codes(9);pos=main.index('public partial class MainWindow')
main=main[:pos]+operator+'\n\n'+main[pos:];pos=main.rfind('}')
main=main[:pos]+handlers+'\n'+main[pos:]
xaml=(W/'MainWindow.xaml').read_text(encoding='utf-8');xaml=re.sub(r'    <WrapPanel.*?</WrapPanel>',lambda m:buttons,xaml,flags=re.S)
(W/'MainWindow.xaml.cs').write_text(main,encoding='utf-8');(W/'MainWindow.xaml').write_text(xaml,encoding='utf-8');build('operator handlers, class and XAML together')
illustration_checkpoint('method-basic')
adapter,checkbox,selection=codes(14)
(W/'HeaderExchange.cs').write_text(adapter,encoding='utf-8')
assert 'var result = CsvStore.Read(path);' in main;main=main.replace('var result = CsvStore.Read(path);',selection,1)
xaml=xaml.replace('    </StackPanel>',checkbox+'\n    </StackPanel>',1)
(W/'MainWindow.xaml.cs').write_text(main,encoding='utf-8');(W/'MainWindow.xaml').write_text(xaml,encoding='utf-8');build('extended header adapter, control and call')
# Reuse the meaningful behavioral checks against the assembled printed code.
checks=W/'checks';checks.mkdir(exist_ok=True)
for p in (R/'tests/ServiceDesk.Checks').glob('*'):
    if p.is_file():shutil.copyfile(p,checks/p.name)
project=next(checks.glob('*.csproj'));value=project.read_text(encoding='utf-8')
value=value.replace('../../stands/ServiceDesk-fixed/ServiceDesk-fixed.csproj',str(W/'ServiceDesk.csproj'))
project.write_text(value,encoding='utf-8')
# Test-only friendship and exclusion; these never enter student archives.
(W/'QaFriend.cs').write_text('using System.Runtime.CompilerServices;\n[assembly: InternalsVisibleTo("ServiceDesk.Checks")]\n',encoding='utf-8')
project_w=W/'ServiceDesk.csproj';project_w.write_text(project_w.read_text(encoding='utf-8').replace('</Project>','<ItemGroup><Compile Remove="checks/**" /></ItemGroup></Project>'),encoding='utf-8')
result=subprocess.run(['dotnet','run','--project',str(project),'--configuration','Release','--',str(R)],text=True,capture_output=True)
assert result.returncode==0,result.stdout+'\n'+result.stderr
print(result.stdout.strip())
