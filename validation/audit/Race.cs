// The fake sensor's timer logic, old and new, with a frame handler that takes 50 ms (longer than the 33 ms period).
using System;
using System.Collections.Generic;
using System.Threading;

class Race
{
    static int frame;
    static readonly object gate = new object();
    static readonly List<int> seen = new List<int>();

    static void Handle(int n) { seen.Add(n); Thread.Sleep(50); }

    static void OldTick(object s) { int n = frame++; lock (gate) Handle(n); }
    static void NewTick(object s) { lock (gate) { int n = frame++; Handle(n); } }

    static int Run(TimerCallback cb)
    {
        frame = 0; seen.Clear();
        using (new Timer(cb, null, 0, 33)) Thread.Sleep(3000);
        Thread.Sleep(500);
        lock (gate)
        {
            int backwards = 0;
            for (int i = 1; i < seen.Count; i++) if (seen[i] <= seen[i - 1]) backwards++;
            return backwards;
        }
    }

    static void Main(string[] args)                  // one logic per process: no callbacks left over from another run
    {
        ThreadPool.SetMinThreads(8, 8);
        bool old = args.Length > 0 && args[0] == "old";
        Console.WriteLine((old ? "old" : "new") + " logic: frames delivered out of order = " + Run(old ? (TimerCallback)OldTick : NewTick)
                          + " of " + seen.Count);
    }
}
