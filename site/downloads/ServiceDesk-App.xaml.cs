using System.Windows;
using System.Globalization;

namespace ServiceDeskWpf;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        var args = e.Args.ToList();
        var checkDate = new DateTime(2026, 10, 1);
        int dateIndex = args.IndexOf("--date");
        if (dateIndex >= 0)
        {
            if (dateIndex + 1 >= args.Count || !DateTime.TryParseExact(args[dateIndex + 1],
                "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out checkDate))
            {
                MessageBox.Show("Параметр --date требует дату yyyy-MM-dd", "Ошибка даты");
                Shutdown(2);
                return;
            }
            args.RemoveRange(dateIndex, 2);
        }
        var runArgs = args.ToArray();
        if (runArgs.Length == 1 && runArgs[0] == "--self-test")
        {
            var rows = TestData.Create(checkDate);
            Console.WriteLine($"test-records={rows.Count}; overdue={TestData.CountOverdue(rows, checkDate)}");
            Shutdown();
            return;
        }
        new MainWindow(runArgs.Length == 1 && runArgs[0] == "--demo", checkDate).Show();
    }
}
