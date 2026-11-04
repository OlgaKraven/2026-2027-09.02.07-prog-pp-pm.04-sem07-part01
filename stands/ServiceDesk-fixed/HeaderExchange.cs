using System.IO;
using System.Text;

namespace ServiceDeskWpf;

// Optional extension: adapt the order, then reuse the accepted strict reader.
internal static class HeaderExchange
{
    private static readonly string[] Columns = ["Id", "Item", "Owner", "Due", "Status"];

    public static ReadResult Read(string path)
    {
        var lines = File.ReadAllLines(path, Encoding.UTF8);
        if (lines.Length == 0) throw new InvalidDataException("Отсутствует заголовок CSV");
        var header = lines[0].TrimStart('\uFEFF').Split(';');
        if (header.Length != Columns.Length || header.Distinct(StringComparer.Ordinal).Count() != Columns.Length ||
            Columns.Any(name => !header.Contains(name, StringComparer.Ordinal)))
            throw new InvalidDataException("Заголовок должен содержать Id, Item, Owner, Due, Status по одному разу");
        var order = Columns.Select(name => Array.IndexOf(header, name)).ToArray();
        var normalized = new List<string> { string.Join(';', Columns) };
        foreach (var line in lines.Skip(1))
        {
            if (string.IsNullOrWhiteSpace(line)) { normalized.Add(line); continue; }
            var cells = line.Split(';');
            // Preserve malformed rows and physical line numbers for the existing validator.
            normalized.Add(cells.Length == Columns.Length ? string.Join(';', order.Select(i => cells[i])) : line);
        }
        var temp = Path.GetTempFileName();
        try { File.WriteAllLines(temp, normalized, Encoding.UTF8); return CsvStore.Read(temp); }
        finally { File.Delete(temp); }
    }
}
