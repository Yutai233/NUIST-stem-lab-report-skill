using System;
using System.IO;
using System.Collections.Generic;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

// x86 STA host for the tested Multisim single-frequency AC / TRAN contract.
class NativeSolve {
    static string output;
    static readonly JavaScriptSerializer json = new JavaScriptSerializer { MaxJsonLength = int.MaxValue };
    static readonly Dictionary<string, object> evidence = new Dictionary<string, object>();
    static void Write(string name, object value) {
        File.WriteAllText(Path.Combine(output, name), json.Serialize(value));
    }
    static void Log(string message) {
        string line = DateTime.Now.ToString("o") + " " + message;
        Console.WriteLine(line);
        File.AppendAllText(Path.Combine(output, "execution.log"), line + Environment.NewLine);
    }
    static Array Read(dynamic circuit, string name, int rows, double timeout, out int method) {
        DateTime end = DateTime.UtcNow.AddSeconds(timeout);
        while (!circuit.OutputReady(name) && DateTime.UtcNow < end) {
            Application.DoEvents(); Thread.Sleep(20);
        }
        if (!circuit.OutputReady(name)) throw new TimeoutException(name + ": " + circuit.LastErrorMessage);
        object data = null; method = 0;
        circuit.GetOutputData(name, ref data, ref method);
        Array values = (Array)data;
        if (values.Rank != 2 || values.GetLength(0) != rows || values.GetLength(1) == 0)
            throw new InvalidDataException("Unexpected output shape: " + name);
        foreach (object item in values) {
            double value = Convert.ToDouble(item);
            if (Double.IsNaN(value) || Double.IsInfinity(value))
                throw new InvalidDataException("Non-finite output: " + name);
        }
        return values;
    }
    [STAThread] static int Main(string[] args) {
        if (args.Length != 3) { Console.Error.WriteLine("Usage: NativeSolve input output config.json"); return 2; }
        output = Path.GetFullPath(args[1]);
        dynamic app = null, circuit = null;
        int code = 1;
        try {
            var config = json.Deserialize<Dictionary<string, object>>(File.ReadAllText(args[2]));
            var settings = (Dictionary<string, object>)config["analysis"];
            double frequency = Convert.ToDouble(settings["frequency_hz"]);
            double duration = Convert.ToDouble(settings["duration_s"]);
            double rate = Convert.ToDouble(settings["sample_rate_hz"]);
            int count = Convert.ToInt32(settings["sample_count"]);
            double timeout = Convert.ToDouble(settings["output_timeout_s"]);
            evidence["analysis"] = settings;
            app = Activator.CreateInstance(Type.GetTypeFromProgID("MultisimInterface.MultisimApp", true));
            app.Connect();
            evidence["software_version"] = Convert.ToString(app.VersionInfo);
            evidence["host_bitness"] = IntPtr.Size * 8;
            Log("connected " + evidence["software_version"]);
            circuit = app.OpenFile(Path.GetFullPath(args[0]));
            Log("opened " + circuit.FileName);
            circuit.ReportNetlist(false, 0, Path.Combine(output, "native_netlist.txt"));
            var available = new List<string>();
            foreach (object name in (Array)circuit.EnumOutputs(0)) available.Add((string)name);
            evidence["available_outputs"] = available;
            var selected = new List<string>();
            if (config.ContainsKey("outputs")) {
                foreach (object name in (System.Collections.IEnumerable)config["outputs"]) selected.Add((string)name);
            } else selected.AddRange(available);
            if (selected.Count == 0) throw new InvalidDataException("No registered outputs");
            foreach (string name in selected)
                if (!available.Contains(name)) throw new InvalidDataException("Output not registered: " + name);
            string[] names = selected.ToArray();
            evidence["selected_outputs"] = names;
            Write("execution.json", evidence);
            var contracts = new Dictionary<string, object>();
            var ac = new Dictionary<string, object>();
            circuit.DoACSingleFrequency(frequency, names);
            foreach (string name in names) {
                int method;
                Array a = Read(circuit, name, 3, timeout, out method);
                if (a.GetLength(1) != 1) throw new InvalidDataException("Expected single-frequency AC");
                double f = Convert.ToDouble(a.GetValue(0, 0));
                if (Math.Abs(f - frequency) > Math.Max(1e-12, frequency * 1e-9))
                    throw new InvalidDataException("AC frequency mismatch: " + name);
                ac[name] = new double[] { f, Convert.ToDouble(a.GetValue(1, 0)), Convert.ToDouble(a.GetValue(2, 0)) };
                contracts["AC:" + name] = new { method = method, shape = new int[] { 3, 1 } };
            }
            Write("ac.json", ac); Log("AC exported");
            if ((int)circuit.SimulationState != 0) circuit.StopSimulation();
            foreach (string name in names) circuit.SetOutputRequest(name, 0, rate, count, false);
            circuit.RunSimulation(duration, false);
            var transient = new Dictionary<string, object>();
            foreach (string name in names) {
                int method;
                Array a = Read(circuit, name, 2, timeout, out method);
                var points = new List<double[]>();
                double previous = Double.NegativeInfinity;
                for (int i = 0; i < a.GetLength(1); i++) {
                    double time = Convert.ToDouble(a.GetValue(0, i));
                    if (time <= previous) throw new InvalidDataException("Non-increasing time: " + name);
                    points.Add(new double[] { time, Convert.ToDouble(a.GetValue(1, i)) }); previous = time;
                }
                transient[name] = points;
                contracts["TRAN:" + name] = new { method = method, shape = new int[] { 2, points.Count },
                    first_time_s = points[0][0], last_time_s = previous };
                Log("TRAN " + name + " points=" + points.Count);
            }
            Write("transient.json", transient);
            evidence["data_contracts"] = contracts;
            evidence["simulation_state"] = Convert.ToInt32(circuit.SimulationState);
            evidence["last_error_message"] = Convert.ToString(circuit.LastErrorMessage);
            circuit.GetCircuitImage(0, Path.Combine(output, "native_schematic.png"));
            circuit.SaveAs(Path.Combine(output, "verified.ms14"));
            Log("saved");
            code = 0;
        } catch (Exception error) {
            evidence["error"] = error.ToString(); Log(error.ToString());
        } finally {
            evidence["native_execution"] = code == 0 ? "PASS" : "FAIL";
            Write("execution.json", evidence);
            if (app != null) {
                try { app.Disconnect(); }
                catch (Exception error) {
                    Log("Disconnect: " + error); code = 1;
                    evidence["disconnect_error"] = error.ToString();
                    evidence["native_execution"] = "FAIL";
                    Write("execution.json", evidence);
                }
            }
        }
        return code;
    }
}
