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
            var rows = CsvStore.Read(e.Args[1]);
            var target = Path.GetTempFileName();
            try
            {
                CsvStore.Write(target, rows);
                Console.WriteLine($"overdue-as-counted={CsvStore.CountOverdue(rows, DateTime.Today)}");
                Console.WriteLine($"export-header={File.ReadLines(target).First()}");
                try { CsvStore.Read(target); }
                catch (Exception ex) { Console.WriteLine($"reimport-error={ex.GetType().Name}"); }
            }
            finally { File.Delete(target); }
            Shutdown();
            return;
        }
        new MainWindow(e.Args.Length == 2 && e.Args[0] == "--demo" ? e.Args[1] : null).Show();
    }
}
