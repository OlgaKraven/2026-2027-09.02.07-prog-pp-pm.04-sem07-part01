using System.Globalization;
using System.Text;
using System.Windows.Forms;

namespace ServiceDesk;

internal record Ticket(int Id, string Item, string Owner, DateTime Due, string Status);

internal static class CsvStore
{
    public static List<Ticket> Read(string path)
    {
        var result = new List<Ticket>();
        foreach (var line in File.ReadAllLines(path, Encoding.UTF8).Skip(1))
        {
            if (string.IsNullOrWhiteSpace(line)) continue;
            var cells = line.Split(';');
            // DEFECT D1: an incomplete row crashes the whole import.
            var id = int.Parse(cells[0]);
            var due = DateTime.ParseExact(cells[3], "dd.MM.yyyy", CultureInfo.InvariantCulture);
            result.Add(new Ticket(id, cells[1], cells[2], due, cells[4]));
        }
        return result;
    }

    public static void Write(string path, IEnumerable<Ticket> tickets)
    {
        // DEFECT D2: export changes the delimiter and date format.
        var lines = new List<string> { "Id,Item,Owner,Due,Status" };
        lines.AddRange(tickets.Select(t => $"{t.Id},{t.Item},{t.Owner},{t.Due:yyyy-MM-dd},{t.Status}"));
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }
}

internal sealed class MainForm : Form
{
    private readonly DataGridView grid = new() { Dock = DockStyle.Fill, ReadOnly = true, AutoGenerateColumns = true };
    private readonly Label status = new() { Dock = DockStyle.Bottom, Height = 28, Text = "Откройте CSV-файл" };
    private List<Ticket> tickets = new();

    public MainForm(string? demoPath = null)
    {
        Text = "Журнал заявок — стенд сопровождения";
        Width = 960;
        Height = 560;
        var bar = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 48 };
        var open = new Button { Text = "Открыть CSV", Width = 140, Height = 32 };
        var save = new Button { Text = "Экспорт CSV", Width = 140, Height = 32 };
        var count = new Button { Text = "Просрочено", Width = 140, Height = 32 };
        open.Click += (_, _) => OpenCsv();
        save.Click += (_, _) => SaveCsv();
        count.Click += (_, _) => CountOverdue();
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
            tickets = CsvStore.Read(path);
            grid.DataSource = tickets.ToList();
            status.Text = $"Загружено записей: {tickets.Count}";
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

    private void CountOverdue()
    {
        // DEFECT D3: completed tickets are incorrectly counted as overdue.
        int value = tickets.Count(t => t.Due < DateTime.Today);
        status.Text = $"Просрочено: {value}";
    }

    [STAThread]
    private static void Main(string[] args)
    {
        if (args.Length == 2 && args[0] == "--self-test")
        {
            var data = CsvStore.Read(args[1]);
            var path = Path.GetTempFileName();
            try
            {
                CsvStore.Write(path, data);
                Console.WriteLine($"loaded={data.Count}; overdue-as-counted={data.Count(t => t.Due < DateTime.Today)}");
                Console.WriteLine($"export-header={File.ReadLines(path).First()}");
                try { CsvStore.Read(path); Console.WriteLine("reimport=success"); }
                catch (Exception ex) { Console.WriteLine($"reimport-error={ex.GetType().Name}"); }
            }
            finally { File.Delete(path); }
            return;
        }
        ApplicationConfiguration.Initialize();
        Application.Run(new MainForm(args.Length == 2 && args[0] == "--demo" ? args[1] : null));
    }
}
