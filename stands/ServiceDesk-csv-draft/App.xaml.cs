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
        if (runArgs.Length == 2 && runArgs[0] == "--self-test")
        {
            var rows = CsvStore.Read(runArgs[1]);
            var target = Path.GetTempFileName();
            try
            {
                CsvStore.Write(target, rows);
                Console.WriteLine($"overdue-as-counted={CsvStore.CountOverdue(rows, checkDate)}");
                Console.WriteLine($"export-header={File.ReadLines(target).First()}");
                try { CsvStore.Read(target); }
                catch (Exception ex) { Console.WriteLine($"reimport-error={ex.GetType().Name}"); }
            }
            finally { File.Delete(target); }
            Shutdown();
            return;
        }
        new MainWindow(runArgs.Length == 2 && runArgs[0] == "--demo" ? runArgs[1] : null, checkDate).Show();
    }
}
