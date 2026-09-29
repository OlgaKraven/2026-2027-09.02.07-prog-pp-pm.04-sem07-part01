using System.Globalization;
using System.Text;
using System.Windows.Forms;

namespace ServiceDeskFixed;

internal record Ticket(int Id, string Item, string Owner, DateTime Due, string Status);
internal record ReadResult(List<Ticket> Tickets, List<string> Warnings);

internal static class CsvStore
{
    private const string Header = "Id;Item;Owner;Due;Status";

    public static ReadResult Read(string path)
    {
        var tickets = new List<Ticket>();
        var warnings = new List<string>();
        var lines = File.ReadAllLines(path, Encoding.UTF8);
        if (lines.Length == 0 || lines[0].TrimStart('\uFEFF') != Header)
            throw new InvalidDataException($"Ожидается заголовок {Header}");
        for (int index = 1; index < lines.Length; index++)
        {
            if (string.IsNullOrWhiteSpace(lines[index])) continue;
            var cells = lines[index].Split(';');
            string? reason = null;
            if (cells.Length != 5) reason = "ожидается пять полей";
            else if (!int.TryParse(cells[0], out _)) reason = "неверный Id";
            else if (string.IsNullOrWhiteSpace(cells[1]) || string.IsNullOrWhiteSpace(cells[2])) reason = "пустое обязательное поле";
            else if (!DateTime.TryParseExact(cells[3], "dd.MM.yyyy", CultureInfo.InvariantCulture, DateTimeStyles.None, out _)) reason = "неверная дата";
            else if (cells[4] != "Открыта" && cells[4] != "Завершена") reason = "неверный статус";
            if (reason != null) { warnings.Add($"Строка {index + 1}: {reason}"); continue; }
            tickets.Add(new Ticket(int.Parse(cells[0], CultureInfo.InvariantCulture), cells[1], cells[2],
                DateTime.ParseExact(cells[3], "dd.MM.yyyy", CultureInfo.InvariantCulture), cells[4]));
        }
        return new ReadResult(tickets, warnings);
    }

    public static void Write(string path, IEnumerable<Ticket> tickets)
    {
        var lines = new List<string> { Header };
        foreach (var t in tickets)
        {
            if (new[] { t.Item, t.Owner, t.Status }.Any(value => value.Contains(';') || value.Contains('\n') || value.Contains('\r')))
                throw new InvalidDataException("В поле нельзя использовать разделитель или перевод строки");
            lines.Add($"{t.Id};{t.Item};{t.Owner};{t.Due.ToString("dd.MM.yyyy", CultureInfo.InvariantCulture)};{t.Status}");
        }
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    public static int CountOverdue(IEnumerable<Ticket> tickets, DateTime today) =>
        tickets.Count(t => t.Status != "Завершена" && t.Due.Date < today.Date);
}

internal sealed class MainForm : Form
{
    private readonly DataGridView grid = new() { Dock = DockStyle.Fill, ReadOnly = true, AutoGenerateColumns = true };
    private readonly Label status = new() { Dock = DockStyle.Bottom, Height = 28, Text = "Откройте CSV-файл" };
    private List<Ticket> tickets = new();

    public MainForm(string? demoPath = null)
    {
        Text = "Журнал заявок — версия 1.1";
        Width = 960;
        Height = 560;
        var bar = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 48 };
        var open = new Button { Text = "Открыть CSV", Width = 140, Height = 32 };
        var save = new Button { Text = "Экспорт CSV", Width = 140, Height = 32 };
        var count = new Button { Text = "Просрочено", Width = 140, Height = 32 };
        open.Click += (_, _) => OpenCsv();
        save.Click += (_, _) => SaveCsv();
        count.Click += (_, _) => status.Text = $"Просрочено: {CsvStore.CountOverdue(tickets, DateTime.Today)}";
        bar.Controls.AddRange(new Control[] { open, save, count });
        Controls.Add(grid);
        Controls.Add(status);
        Controls.Add(bar);
        if (demoPath != null) Shown += (_, _) => LoadCsv(demoPath);
    }

    private void OpenCsv()
    {
        using var dialog = new OpenFileDialog { Filter = "CSV (*.csv)|*.csv" };
        if (dialog.ShowDialog() != DialogResult.OK) return;
        LoadCsv(dialog.FileName);
    }

    private void LoadCsv(string path)
    {
        try
        {
            var result = CsvStore.Read(path);
            tickets = result.Tickets;
            grid.DataSource = tickets.ToList();
            status.Text = $"Загружено: {tickets.Count}; пропущено: {result.Warnings.Count}";
            if (result.Warnings.Count > 0) MessageBox.Show(string.Join(Environment.NewLine, result.Warnings), "Предупреждения импорта");
        }
        catch (Exception ex) { MessageBox.Show(ex.Message, "Ошибка импорта"); }
    }

    private void SaveCsv()
    {
        using var dialog = new SaveFileDialog { Filter = "CSV (*.csv)|*.csv", FileName = "export.csv" };
        if (dialog.ShowDialog() != DialogResult.OK) return;
        try { CsvStore.Write(dialog.FileName, tickets); status.Text = "Файл сохранён"; }
        catch (Exception ex) { MessageBox.Show(ex.Message, "Ошибка экспорта"); }
    }

    [STAThread]
    private static void Main(string[] args)
    {
        if (args.Length == 2 && args[0] == "--self-test")
        {
            var result = CsvStore.Read(args[1]);
            var target = Path.GetTempFileName();
            try
            {
                CsvStore.Write(target, result.Tickets);
                var roundtrip = CsvStore.Read(target);
                if (roundtrip.Warnings.Count != 0 || !result.Tickets.SequenceEqual(roundtrip.Tickets))
                    throw new InvalidOperationException("Повторный импорт не совпал");
                Console.WriteLine($"tickets={result.Tickets.Count}; warnings={result.Warnings.Count}; overdue={CsvStore.CountOverdue(result.Tickets, DateTime.Today)}");
                foreach (var warning in result.Warnings) Console.WriteLine(warning);
            }
            finally { File.Delete(target); }
            return;
        }
        ApplicationConfiguration.Initialize();
        Application.Run(new MainForm(args.Length == 2 && args[0] == "--demo" ? args[1] : null));
    }
}
