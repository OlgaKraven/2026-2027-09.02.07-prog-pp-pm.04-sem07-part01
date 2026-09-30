using System.Globalization;
using System.IO;
using System.Text;
using System.Windows;
using Microsoft.Win32;

namespace ServiceDeskWpf;

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

public partial class MainWindow : Window
{
    private List<Ticket> tickets = new();

    public MainWindow(string? demoPath = null)
    {
        InitializeComponent();
        if (demoPath != null) Loaded += (_, _) =>
            Dispatcher.BeginInvoke(System.Windows.Threading.DispatcherPriority.ApplicationIdle,
                new Action(() => LoadCsv(demoPath)));
    }

    private void OpenCsv_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog { Filter = "CSV (*.csv)|*.csv" };
        if (dialog.ShowDialog() == true) LoadCsv(dialog.FileName);
    }

    private void LoadCsv(string path)
    {
        try
        {
            var result = CsvStore.Read(path);
            tickets = result.Tickets;
            TicketsGrid.ItemsSource = tickets.ToList();
            StatusText.Text = $"Загружено: {tickets.Count}; пропущено: {result.Warnings.Count}";
            if (result.Warnings.Count > 0)
                MessageBox.Show(string.Join(Environment.NewLine, result.Warnings), "Предупреждения импорта");
        }
        catch (Exception ex) { MessageBox.Show(ex.Message, "Ошибка импорта"); }
    }

    private void SaveCsv_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new SaveFileDialog { Filter = "CSV (*.csv)|*.csv", FileName = "export.csv" };
        if (dialog.ShowDialog() != true) return;
        try { CsvStore.Write(dialog.FileName, tickets); StatusText.Text = "Файл сохранён"; }
        catch (Exception ex) { MessageBox.Show(ex.Message, "Ошибка экспорта"); }
    }

    private void CountOverdue_Click(object sender, RoutedEventArgs e) =>
        StatusText.Text = $"Просрочено: {CsvStore.CountOverdue(tickets, DateTime.Today)}";
}
