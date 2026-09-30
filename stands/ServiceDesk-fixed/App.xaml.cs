using System.IO;
using System.Windows;

namespace ServiceDeskWpf;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        if (e.Args.Length == 2 && e.Args[0] == "--self-test")
        {
            var result = CsvStore.Read(e.Args[1]);
            var target = Path.GetTempFileName();
            try
            {
                CsvStore.Write(target, result.Tickets);
                var again = CsvStore.Read(target);
                if (again.Warnings.Count != 0 || !result.Tickets.SequenceEqual(again.Tickets))
                    throw new InvalidOperationException("Повторный импорт не совпал");
                Console.WriteLine($"tickets={result.Tickets.Count}; warnings={result.Warnings.Count}; overdue={CsvStore.CountOverdue(result.Tickets, DateTime.Today)}");
                foreach (var warning in result.Warnings) Console.WriteLine(warning);
            }
            finally { File.Delete(target); }
            Shutdown();
            return;
        }
        new MainWindow(e.Args.Length == 2 && e.Args[0] == "--demo" ? e.Args[1] : null).Show();
    }
}
