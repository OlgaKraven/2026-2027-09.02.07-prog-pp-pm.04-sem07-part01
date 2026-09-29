using System.Windows.Forms;

namespace ServiceDesk;

internal record Ticket(int Id, string Item, string Owner, DateTime Due, string Status);

internal static class TestData
{
    public static List<Ticket> Create(DateTime today) =>
    [
        new Ticket(101, "Проектор", "Ирина", today.AddDays(-2), "Открыта"),
        new Ticket(102, "Ноутбук", "Павел", today.AddDays(-1), "Завершена")
    ];

    public static int CountOverdue(IEnumerable<Ticket> tickets, DateTime today) =>
        tickets.Count(t => t.Status != "Завершена" && t.Due.Date < today.Date);
}

internal sealed class MainForm : Form
{
    private readonly DataGridView grid = new() { Dock = DockStyle.Fill, ReadOnly = true, AutoGenerateColumns = true };
    private readonly Label status = new() { Dock = DockStyle.Bottom, Height = 28, Text = "Сначала загрузите встроенные тестовые данные" };
    private List<Ticket> tickets = new();

    public MainForm(bool showTestData = false)
    {
        Text = "Журнал заявок — проверка приложения";
        Width = 960;
        Height = 560;
        var bar = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 48 };
        var load = new Button { Text = "Тестовые данные", Width = 150, Height = 32 };
        var count = new Button { Text = "Просрочено", Width = 140, Height = 32 };
        load.Click += (_, _) => LoadTestData();
        count.Click += (_, _) => status.Text = $"Просрочено: {TestData.CountOverdue(tickets, DateTime.Today)}";
        bar.Controls.AddRange(new Control[] { load, count });
        Controls.Add(grid);
        Controls.Add(status);
        Controls.Add(bar);
        if (showTestData) Shown += (_, _) => LoadTestData();
    }

    private void LoadTestData()
    {
        tickets = TestData.Create(DateTime.Today);
        grid.DataSource = tickets.ToList();
        status.Text = $"Тестовых записей: {tickets.Count}";
    }

    [STAThread]
    private static void Main(string[] args)
    {
        if (args.Length == 1 && args[0] == "--self-test")
        {
            var data = TestData.Create(DateTime.Today);
            Console.WriteLine($"test-records={data.Count}; overdue={TestData.CountOverdue(data, DateTime.Today)}");
            return;
        }
        ApplicationConfiguration.Initialize();
        Application.Run(new MainForm(args.Length == 1 && args[0] == "--demo"));
    }
}
