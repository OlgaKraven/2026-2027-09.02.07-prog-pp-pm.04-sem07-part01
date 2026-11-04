using System.Text;
using System.Text.Json;
using ServiceDeskWpf;

string root = Path.GetFullPath(args.Length > 0 ? args[0] : ".");
string data = Path.Combine(root, "stands", "data");
string work = Path.Combine(root, ".work", "checks");
Directory.CreateDirectory(work);
var checks = new List<string>();
void Check(bool ok, string name)
{
    if (!ok) throw new InvalidOperationException(name);
    checks.Add(name);
}
void Reject(Action action, string name)
{
    try { action(); } catch (InvalidDataException) { checks.Add(name); return; }
    throw new InvalidOperationException(name);
}
var date = new DateTime(2026, 10, 1);
var builtIn = TestData.Create(date);
Check(builtIn.Count == 2 && CsvStore.CountOverdue(builtIn, date) == 1, "built-in: two rows, one overdue");
var partial = CsvStore.Read(Path.Combine(data, "demo.csv"));
Check(partial.Tickets.Count == 2 && partial.Warnings.Count == 1 && partial.Warnings[0].StartsWith("Строка 4:"), "partial file: two rows and physical line 4");
for (int id = 1; id <= 30; id++)
{
    var input = CsvStore.Read(Path.Combine(data, $"variant-{id:00}.csv"));
    Check(input.Tickets.Count == 2 && input.Warnings.Count == 1 && input.Warnings[0].StartsWith("Строка 4:"), $"variant {id:00}: core import");
    string output = Path.Combine(work, $"roundtrip-{id:00}.csv");
    CsvStore.Write(output, input.Tickets);
    var again = CsvStore.Read(output);
    Check(input.Tickets.SequenceEqual(again.Tickets) && again.Warnings.Count == 0, $"variant {id:00}: all five fields roundtrip");
    var control = CsvStore.Read(Path.Combine(data, $"variant-check-{id:00}.csv"));
    Check(control.Tickets.Count == 6 && control.Warnings.Count == 0, $"variant {id:00}: six valid control rows");
}
var all = CsvStore.Read(Path.Combine(data, "demo-operator.csv")).Tickets;
var selected = OperatorView.Select(all, date);
Check(selected.Select(t => t.Id).SequenceEqual(new[] {105,101,103}), "control date: exact demo selection");
Check(OperatorView.Select(all, new DateTime(2026,11,4)).Count == 5, "another date: rule uses supplied date");
Check(all.Count == 6, "selection does not shorten the full list");
string export = Path.Combine(work, "all-after-selection.csv");
CsvStore.Write(export, all);
Check(CsvStore.Read(export).Tickets.SequenceEqual(all), "export after selection preserves the complete list");
var boundaries = new[] { new Ticket(1,"A","O",date.AddDays(-1),"Открыта"), new Ticket(2,"B","O",date.AddDays(-1),"Завершена"), new Ticket(3,"C","O",date,"Открыта") };
Check(CsvStore.CountOverdue(boundaries, date) == 1, "overdue boundaries: past open, past closed, today");
string invalid = Path.Combine(work,"invalid.csv");
File.WriteAllText(invalid,"Id;Item;Owner;Due;Status\n\n101;A;O;28.09.2026;Открыта\nbad\n102;B;O;30.09.2026;Завершена\n",Encoding.UTF8);
var mixed=CsvStore.Read(invalid);
Check(mixed.Tickets.Count==2 && mixed.Warnings.Single().StartsWith("Строка 4:"),"bad middle row and blank line preserve physical numbering");
foreach(var bad in new[]{"x;A;O;01.10.2026;Открыта","1;;O;01.10.2026;Открыта","1;A;;01.10.2026;Открыта","1;A;O;31.02.2026;Открыта","1;A;O;01.10.2026;Unknown"})
{
    File.WriteAllText(invalid,"Id;Item;Owner;Due;Status\n"+bad+"\n",Encoding.UTF8);
    var result=CsvStore.Read(invalid);
    Check(result.Tickets.Count==0 && result.Warnings.Count==1,"reject row: "+bad);
}
File.WriteAllText(invalid,"Id;Item;Owner;Due;Status\n",Encoding.UTF8);
Check(CsvStore.Read(invalid).Tickets.Count==0,"header-only file is an empty accepted list");
File.WriteAllText(invalid,"",Encoding.UTF8);
Reject(()=>CsvStore.Read(invalid),"empty file has no header");
Reject(()=>CsvStore.Read(Path.Combine(data,"demo-bad-header.csv")),"strict reader rejects invalid header");
Reject(()=>CsvStore.Read(Path.Combine(data,"demo-reordered.csv")),"strict route rejects reordered header");
var adapted=HeaderExchange.Read(Path.Combine(data,"demo-reordered.csv"));
Check(adapted.Warnings.Count==0 && adapted.Tickets.SequenceEqual(all),"extension: reordered columns preserve every field");
Check(HeaderExchange.Read(Path.Combine(data,"demo-operator.csv")).Tickets.SequenceEqual(all),"extension: old canonical format remains readable");
Reject(()=>HeaderExchange.Read(Path.Combine(data,"demo-bad-header.csv")),"extension: duplicate and missing column rejected");
foreach(var header in new[]{"Id;Item;Owner;Due;Unknown","Id;Item;Owner;Due"})
{
    File.WriteAllText(invalid,header+"\n",Encoding.UTF8);
    Reject(()=>HeaderExchange.Read(invalid),"extension: invalid columns: "+header);
}
File.WriteAllText(invalid,"Owner;Status;Id;Due;Item\nO;Открыта;101;28.09.2026;A\nbad\n",Encoding.UTF8);
var adaptedPartial=HeaderExchange.Read(invalid);
Check(adaptedPartial.Tickets.Count==1 && adaptedPartial.Warnings.Single().StartsWith("Строка 3:"),"extension: physical warning line preserved");
string sentinel=Path.Combine(work,"do-not-overwrite.csv");
File.WriteAllText(sentinel,"original",Encoding.UTF8);
Reject(()=>CsvStore.Write(sentinel,[new Ticket(1,"A;B","O",date,"Открыта")]),"separator inside field rejected before writing");
Check(File.ReadAllText(sentinel,Encoding.UTF8)=="original","failed export preserves previous file");
string backup=Path.Combine(work,"before.csv");
File.Copy(Path.Combine(data,"demo-valid.csv"),backup,true);
string active=Path.Combine(work,"work.csv");
File.Copy(backup,active,true);
CsvStore.Write(active,all);
File.Copy(backup,active,true);
Check(File.ReadAllBytes(active).SequenceEqual(File.ReadAllBytes(backup)),"rollback restores exact source CSV bytes");
File.WriteAllText(Path.Combine(root,".work","checks.json"),JsonSerializer.Serialize(new { passed=checks.Count, checks, scope="Core import/export for 30 data sets; demo selection and exchange adapter. Individual OperatorView implementations are student work and are not claimed as tested." },new JsonSerializerOptions {WriteIndented=true}));
Console.WriteLine($"PASS: {checks.Count} checks");
