using System.Windows;

namespace ServiceDeskWpf;

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

public partial class MainWindow : Window
{
    private List<Ticket> tickets = new();
    private DateTime CheckDate => ControlDate.SelectedDate!.Value.Date;

    public MainWindow(bool showTestData = false, DateTime? checkDate = null)
    {
        InitializeComponent();
        ControlDate.SelectedDate = checkDate ?? new DateTime(2026, 10, 1);
        if (showTestData) Loaded += (_, _) => LoadTestData();
    }

    private void ControlDate_Changed(object sender, System.Windows.Controls.SelectionChangedEventArgs e)
    {
        if (ControlDate.SelectedDate is null)
            ControlDate.SelectedDate = new DateTime(2026, 10, 1);
    }

    private void LoadTestData_Click(object sender, RoutedEventArgs e) => LoadTestData();

    private void LoadTestData()
    {
        tickets = TestData.Create(CheckDate);
        TicketsGrid.ItemsSource = tickets.ToList();
        StatusText.Text = $"Тестовых записей: {tickets.Count}";
    }

    private void CountOverdue_Click(object sender, RoutedEventArgs e) =>
        StatusText.Text = $"Просрочено: {TestData.CountOverdue(tickets, CheckDate)}";
}
