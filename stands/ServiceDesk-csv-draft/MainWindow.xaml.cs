using System.Globalization;
using System.IO;
using System.Text;
using System.Windows;
using Microsoft.Win32;

namespace ServiceDeskWpf;

internal record Ticket(int Id, string Item, string Owner, DateTime Due, string Status);

internal static class CsvStore
{
    public static List<Ticket> Read(string path)
    {
        var rows = new List<Ticket>();
        foreach (var line in File.ReadAllLines(path, Encoding.UTF8).Skip(1))
        {
            if (string.IsNullOrWhiteSpace(line)) continue;
            var cells = line.Split(';');
            rows.Add(new Ticket(int.Parse(cells[0]), cells[1], cells[2],
                DateTime.ParseExact(cells[3], "dd.MM.yyyy", CultureInfo.InvariantCulture), cells[4]));
        }
        return rows;
    }

    public static void Write(string path, IEnumerable<Ticket> rows)
    {
        var lines = new List<string> { "Id,Item,Owner,Due,Status" };
        lines.AddRange(rows.Select(t => $"{t.Id},{t.Item},{t.Owner},{t.Due:yyyy-MM-dd},{t.Status}"));
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    public static int CountOverdue(IEnumerable<Ticket> rows, DateTime today) =>
        rows.Count(t => t.Due.Date < today.Date);
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
            tickets = CsvStore.Read(path);
            TicketsGrid.ItemsSource = tickets.ToList();
            StatusText.Text = $"Загружено: {tickets.Count}";
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
