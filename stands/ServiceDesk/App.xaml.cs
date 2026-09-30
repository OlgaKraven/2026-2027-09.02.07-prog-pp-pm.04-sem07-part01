using System.Windows;

namespace ServiceDeskWpf;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        if (e.Args.Length == 1 && e.Args[0] == "--self-test")
        {
            var rows = TestData.Create(DateTime.Today);
            Console.WriteLine($"test-records={rows.Count}; overdue={TestData.CountOverdue(rows, DateTime.Today)}");
            Shutdown();
            return;
        }
        new MainWindow(e.Args.Length == 1 && e.Args[0] == "--demo").Show();
    }
}
