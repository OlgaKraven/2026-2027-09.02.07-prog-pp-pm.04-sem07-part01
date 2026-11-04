using System.IO;
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
        if (runArgs.Length == 1 && runArgs[0] == "--test-built-in")
        {
            var rows = TestData.Create(checkDate);
            Console.WriteLine($"test-records={rows.Count}; overdue={CsvStore.CountOverdue(rows, checkDate)}");
            Shutdown();
            return;
        }
        if (runArgs.Length == 2 && runArgs[0] == "--self-test")
        {
            var result = CsvStore.Read(runArgs[1]);
            var target = Path.GetTempFileName();
            try
            {
                CsvStore.Write(target, result.Tickets);
                var again = CsvStore.Read(target);
                if (again.Warnings.Count != 0 || !result.Tickets.SequenceEqual(again.Tickets))
                    throw new InvalidOperationException("Повторный импорт не совпал");
                Console.WriteLine($"tickets={result.Tickets.Count}; warnings={result.Warnings.Count}; overdue={CsvStore.CountOverdue(result.Tickets, checkDate)}");
                foreach (var warning in result.Warnings) Console.WriteLine(warning);
            }
            finally { File.Delete(target); }
            Shutdown();
            return;
        }
        new MainWindow(runArgs.Length == 2 && runArgs[0] == "--demo" ? runArgs[1] : null, checkDate).Show();
    }
}
