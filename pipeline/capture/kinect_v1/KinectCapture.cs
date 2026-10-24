// KinectCapture: record a Kinect v1 (Kinect for Xbox 360 / Kinect for Windows) session for rehabtwin.
//
// Windows only: needs the Kinect for Windows SDK 1.8 (driver + Microsoft.Kinect.dll) and, for an Xbox 360
// sensor, its USB/power adapter. Build with build.cmd (the C# compiler that ships with Windows, C# 5).
//
//   KinectCapture.exe OUT_DIR [--seconds N] [--countdown S] [--jpeg-quality Q]
//
// Writes OUT_DIR/ (format "rehabtwin-kinect-v1/1", read by rehabtwin/kinect.py):
//   colour/000000.jpg ...   640x480 colour frames, one per recorded frame
//   depth_registered.u16    per frame 640x480 uint16 little-endian depth in mm on the COLOUR pixel grid
//                           (CoordinateMapper.MapDepthFrameToColorFrame, the sensor's factory calibration;
//                           0 = no depth). This is what the keypoints are lifted with.
//   depth_raw.u16           per frame 640x480 uint16 depth in mm on the depth camera's own grid (0 = unknown)
//   frames.csv              one row per recorded frame: sensor frame numbers and timestamps, host time,
//                           accelerometer, SDK floor plane, tracked skeleton id
//   skeleton.csv            the SDK's 20-joint skeleton of the nearest tracked person, in skeleton space (m)
//                           and in colour pixels: a Tier-C baseline and the left/right (mirroring) check
//   meta.json               sensor id, formats, nominal intrinsics, elevation, counts
//
// Nothing here estimates posture; it only records. Intrinsics are the SDK's nominal values, not a
// calibration of this unit.
using System;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using Microsoft.Kinect;

static class KinectCapture
{
    static volatile bool stop;

    static int Main(string[] args)
    {
        string outDir = null;
        double seconds = 0, countdown = 5;
        long quality = 92;
        for (int i = 0; i < args.Length; i++)
        {
            string a = args[i];
            if (a == "--seconds" && i + 1 < args.Length) seconds = double.Parse(args[++i], CultureInfo.InvariantCulture);
            else if (a == "--countdown" && i + 1 < args.Length) countdown = double.Parse(args[++i], CultureInfo.InvariantCulture);
            else if (a == "--jpeg-quality" && i + 1 < args.Length) quality = long.Parse(args[++i], CultureInfo.InvariantCulture);
            else if (a.StartsWith("--")) { Usage("unknown option " + a); return 2; }
            else if (outDir == null) outDir = a;
            else { Usage("unexpected argument " + a); return 2; }
        }
        if (outDir == null) { Usage("OUT_DIR is required"); return 2; }
        if (Directory.Exists(outDir) && Directory.EnumerateFileSystemEntries(outDir).Any())
        {
            Console.Error.WriteLine("refused: " + outDir + " is not empty (one recording per folder)");
            return 2;
        }

        KinectSensor sensor = KinectSensor.KinectSensors.FirstOrDefault(s => s.Status == KinectStatus.Connected);
        if (sensor == null)
        {
            Console.Error.WriteLine("no connected Kinect v1 found. Check: Kinect for Windows SDK 1.8 installed; the Xbox 360 "
                                    + "sensor's USB/power adapter plugged into mains; a USB 2.0 port without other "
                                    + "cameras on the same controller; Kinect Studio and other Kinect apps closed.");
            return 1;
        }

        sensor.ColorStream.Enable(ColorImageFormat.RgbResolution640x480Fps30);
        sensor.DepthStream.Enable(DepthImageFormat.Resolution640x480Fps30);
        sensor.SkeletonStream.Enable();      // default: standing mode, no smoothing (raw joint positions)
        Recorder rec = new Recorder(outDir, sensor, quality);
        sensor.AllFramesReady += rec.OnFrames;
        Console.CancelKeyPress += delegate(object s, ConsoleCancelEventArgs e) { e.Cancel = true; stop = true; };
        sensor.Start();
        try
        {
            Console.WriteLine("Framing check (not recording yet). Stand where you will exercise; whole body, both feet "
                              + "and some floor in view, about 2.5-3 m from the sensor.");
            Stopwatch t = Stopwatch.StartNew();
            while (!stop && t.Elapsed.TotalSeconds < countdown)
            {
                Console.WriteLine(string.Format(CultureInfo.InvariantCulture, "  {0,4:0}s  {1}",
                                                countdown - t.Elapsed.TotalSeconds, rec.Status));
                Thread.Sleep(1000);
            }
            if (stop) { Console.WriteLine("cancelled before recording"); return 1; }
            rec.Begin();
            Console.WriteLine(seconds > 0
                ? string.Format(CultureInfo.InvariantCulture, "RECORDING for {0:0} s. Jump once now (camera sync).", seconds)
                : "RECORDING. Jump once now (camera sync). Press Enter or Ctrl+C to stop.");
            t.Restart();
            double lastPrint = 0;
            while (!stop && (seconds <= 0 || t.Elapsed.TotalSeconds < seconds))
            {
                if (seconds <= 0 && Console.KeyAvailable && Console.ReadKey(true).Key == ConsoleKey.Enter) break;
                if (t.Elapsed.TotalSeconds - lastPrint >= 1.0)
                {
                    lastPrint = t.Elapsed.TotalSeconds;
                    Console.WriteLine(string.Format(CultureInfo.InvariantCulture, "  {0,5:0}s  {1} frames  {2}",
                                                    lastPrint, rec.Written, rec.Status));
                }
                Thread.Sleep(50);
            }
        }
        finally
        {
            rec.EndRecording();
            sensor.AllFramesReady -= rec.OnFrames;
            sensor.Stop();
            rec.Finish();
        }
        Console.WriteLine(string.Format(CultureInfo.InvariantCulture,
            "wrote {0} frames to {1} ({2} incomplete frame events skipped, {3} sensor frames missed)",
            rec.Written, outDir, rec.Incomplete, rec.Missed));
        return 0;
    }

    static void Usage(string why)
    {
        Console.Error.WriteLine(why);
        Console.Error.WriteLine("usage: KinectCapture.exe OUT_DIR [--seconds N] [--countdown S] [--jpeg-quality Q]");
    }
}

sealed class Recorder
{
    public const string Format = "rehabtwin-kinect-v1/1";
    const int W = 640, H = 480;
    // Nominal intrinsics (NuiSensor.h: NUI_CAMERA_COLOR_NOMINAL_FOCAL_LENGTH_IN_PIXELS for 640x480 colour,
    // 2 x NUI_CAMERA_DEPTH_NOMINAL_FOCAL_LENGTH_IN_PIXELS for 640x480 depth). Not a calibration of this unit.
    const double ColourFocalPx = 531.15, DepthFocalPx = 571.26;
    static readonly JointType[] Joints = (JointType[])Enum.GetValues(typeof(JointType));

    readonly string dir;
    readonly KinectSensor sensor;
    readonly long quality;
    readonly object gate = new object();
    readonly BlockingCollection<Tuple<int, byte[]>> jpegQueue = new BlockingCollection<Tuple<int, byte[]>>(60);
    readonly Thread jpegThread;
    readonly DepthImagePixel[] depthPixels = new DepthImagePixel[W * H];
    readonly ColorImagePoint[] colourPoints = new ColorImagePoint[W * H];
    readonly ushort[] registered = new ushort[W * H];
    readonly ushort[] raw = new ushort[W * H];
    readonly byte[] depthBytes = new byte[W * H * 2];
    readonly Skeleton[] skeletons = new Skeleton[6];
    readonly Stopwatch clock = new Stopwatch();
    BinaryWriter depthReg, depthRaw;
    StreamWriter framesCsv, skeletonCsv;
    DateTime startUtc;
    string sensorId, connectionId;
    int elevationDeg;
    bool recording;
    int lastColourFrame = -1;
    Vector4 accel;
    int accelAge = int.MaxValue;
    public int Written, Incomplete, Missed;
    public volatile string Status = "waiting for frames";

    public Recorder(string dir, KinectSensor sensor, long quality)
    {
        this.dir = dir;
        this.sensor = sensor;
        this.quality = quality;
        Directory.CreateDirectory(Path.Combine(dir, "colour"));
        jpegThread = new Thread(WriteJpegs) { IsBackground = false, Name = "jpeg" };
        jpegThread.Start();
    }

    public void Begin()
    {
        lock (gate)
        {
            depthReg = new BinaryWriter(File.Create(Path.Combine(dir, "depth_registered.u16")));
            depthRaw = new BinaryWriter(File.Create(Path.Combine(dir, "depth_raw.u16")));
            framesCsv = new StreamWriter(Path.Combine(dir, "frames.csv"), false, new UTF8Encoding(false));
            framesCsv.WriteLine("frame,colour_frame_number,colour_timestamp_ms,depth_frame_number,depth_timestamp_ms,"
                                + "host_ms,accel_x,accel_y,accel_z,floor_a,floor_b,floor_c,floor_d,skeleton_id");
            skeletonCsv = new StreamWriter(Path.Combine(dir, "skeleton.csv"), false, new UTF8Encoding(false));
            skeletonCsv.WriteLine("frame,joint,state,x,y,z,u,v");
            sensorId = sensor.UniqueKinectId;          // read while the sensor runs
            connectionId = sensor.DeviceConnectionId;
            elevationDeg = sensor.ElevationAngle;
            startUtc = DateTime.UtcNow;
            clock.Start();
            recording = true;
        }
    }

    public void EndRecording()
    {
        lock (gate) { recording = false; }
    }

    public void OnFrames(object sender, AllFramesReadyEventArgs e)
    {
        using (ColorImageFrame colour = e.OpenColorImageFrame())
        using (DepthImageFrame depth = e.OpenDepthImageFrame())
        using (SkeletonFrame skel = e.OpenSkeletonFrame())
        {
            Skeleton body = null;
            Tuple<float, float, float, float> floor = Tuple.Create(0f, 0f, 0f, 0f);
            if (skel != null)
            {
                skel.CopySkeletonDataTo(skeletons);
                floor = skel.FloorClipPlane;
                body = skeletons.Where(s => s != null && s.TrackingState == SkeletonTrackingState.Tracked)
                                .OrderBy(s => s.Position.Z).FirstOrDefault();
            }
            Status = Describe(body, floor);
            lock (gate)
            {
                if (!recording) return;
                if (colour == null || depth == null) { Incomplete++; return; }
                if (lastColourFrame >= 0 && colour.FrameNumber > lastColourFrame + 1)
                    Missed += colour.FrameNumber - lastColourFrame - 1;
                lastColourFrame = colour.FrameNumber;

                byte[] bgra = new byte[colour.PixelDataLength];
                colour.CopyPixelDataTo(bgra);
                jpegQueue.Add(Tuple.Create(Written, bgra));      // blocks if the disk falls behind: frames are missed, not misaligned

                depth.CopyDepthImagePixelDataTo(depthPixels);
                sensor.CoordinateMapper.MapDepthFrameToColorFrame(DepthImageFormat.Resolution640x480Fps30, depthPixels,
                                                                  ColorImageFormat.RgbResolution640x480Fps30, colourPoints);
                Array.Clear(registered, 0, registered.Length);
                for (int i = 0; i < depthPixels.Length; i++)
                {
                    ushort d = depthPixels[i].IsKnownDepth && depthPixels[i].Depth > 0 ? (ushort)depthPixels[i].Depth : (ushort)0;
                    raw[i] = d;
                    if (d == 0) continue;
                    ColorImagePoint p = colourPoints[i];
                    if (p.X < 0 || p.X >= W || p.Y < 0 || p.Y >= H) continue;
                    int k = p.Y * W + p.X;
                    if (registered[k] == 0 || d < registered[k]) registered[k] = d;   // nearest surface wins
                }
                WriteDepth(depthReg, registered);
                WriteDepth(depthRaw, raw);

                if (accelAge >= 30)          // gravity does not change; one reading a second is plenty
                {
                    accel = sensor.AccelerometerGetCurrentReading();
                    accelAge = 0;
                }
                accelAge++;
                framesCsv.WriteLine(string.Join(",", new string[] {
                    I(Written), I(colour.FrameNumber), L(colour.Timestamp), I(depth.FrameNumber), L(depth.Timestamp),
                    F(clock.Elapsed.TotalMilliseconds), F(accel.X), F(accel.Y), F(accel.Z),
                    F(floor.Item1), F(floor.Item2), F(floor.Item3), F(floor.Item4),
                    body == null ? "" : I(body.TrackingId) }));
                if (body != null)
                {
                    foreach (JointType j in Joints)
                    {
                        Joint joint = body.Joints[j];
                        ColorImagePoint uv = sensor.CoordinateMapper.MapSkeletonPointToColorPoint(
                            joint.Position, ColorImageFormat.RgbResolution640x480Fps30);
                        skeletonCsv.WriteLine(string.Join(",", new string[] {
                            I(Written), j.ToString(), joint.TrackingState.ToString(),
                            F(joint.Position.X), F(joint.Position.Y), F(joint.Position.Z), I(uv.X), I(uv.Y) }));
                    }
                }
                Written++;
            }
        }
    }

    void WriteDepth(BinaryWriter w, ushort[] mm)
    {
        Buffer.BlockCopy(mm, 0, depthBytes, 0, depthBytes.Length);      // little-endian on every Windows PC
        w.Write(depthBytes);
    }

    void WriteJpegs()
    {
        ImageCodecInfo jpeg = ImageCodecInfo.GetImageEncoders().First(c => c.FormatID == ImageFormat.Jpeg.Guid);
        EncoderParameters p = new EncoderParameters(1);
        p.Param[0] = new EncoderParameter(System.Drawing.Imaging.Encoder.Quality, quality);
        foreach (Tuple<int, byte[]> item in jpegQueue.GetConsumingEnumerable())
        {
            using (Bitmap bmp = new Bitmap(W, H, PixelFormat.Format32bppRgb))     // Kinect colour is BGRX, GDI+'s layout
            {
                BitmapData data = bmp.LockBits(new Rectangle(0, 0, W, H), ImageLockMode.WriteOnly, PixelFormat.Format32bppRgb);
                for (int y = 0; y < H; y++)
                    Marshal.Copy(item.Item2, y * W * 4, data.Scan0 + y * data.Stride, W * 4);
                bmp.UnlockBits(data);
                bmp.Save(Path.Combine(dir, "colour", item.Item1.ToString("000000") + ".jpg"), jpeg, p);
            }
        }
    }

    public void Finish()
    {
        jpegQueue.CompleteAdding();
        jpegThread.Join();
        lock (gate)
        {
            if (depthReg != null) { depthReg.Close(); depthRaw.Close(); framesCsv.Close(); skeletonCsv.Close(); }
        }
        StringBuilder m = new StringBuilder();
        m.Append("{\n");
        m.Append("  \"format\": \"").Append(Format).Append("\",\n");
        m.Append("  \"sdk\": \"Kinect for Windows SDK 1.8, Microsoft.Kinect ")
         .Append(typeof(KinectSensor).Assembly.GetName().Version).Append("\",\n");
        m.Append("  \"sensor_id\": ").Append(Q(sensorId)).Append(",\n");
        m.Append("  \"device_connection_id\": ").Append(Q(connectionId)).Append(",\n");
        m.Append("  \"started_at\": \"").Append(startUtc.ToString("yyyy-MM-ddTHH:mm:ss.fffZ", CultureInfo.InvariantCulture)).Append("\",\n");
        m.Append("  \"fps\": 30,\n");
        m.Append("  \"frames\": ").Append(I(Written)).Append(",\n");
        m.Append("  \"incomplete_frame_events\": ").Append(I(Incomplete)).Append(",\n");
        m.Append("  \"sensor_frames_missed\": ").Append(I(Missed)).Append(",\n");
        m.Append("  \"elevation_angle_deg\": ").Append(I(elevationDeg)).Append(",\n");
        m.Append("  \"colour\": {\"width\": 640, \"height\": 480, \"format\": \"RgbResolution640x480Fps30\", \"jpeg_quality\": ")
         .Append(quality.ToString(CultureInfo.InvariantCulture))
         .Append(", \"focal_px\": ").Append(F(ColourFocalPx)).Append(", \"cx\": 320, \"cy\": 240, \"intrinsics_source\": ")
         .Append("\"nominal (NuiSensor.h), not calibrated\"},\n");
        m.Append("  \"depth\": {\"width\": 640, \"height\": 480, \"format\": \"Resolution640x480Fps30\", \"unit\": \"mm\", ")
         .Append("\"focal_px\": ").Append(F(DepthFocalPx)).Append(", \"registered\": \"depth_registered.u16: nearest depth ")
         .Append("splatted onto colour pixels with CoordinateMapper.MapDepthFrameToColorFrame\"},\n");
        m.Append("  \"skeleton\": \"SDK 1.8, standing mode, no smoothing; skeleton space metres, x to the sensor's ")
         .Append("left, y up, z out of the sensor\",\n");
        m.Append("  \"accelerometer\": \"KinectSensor.AccelerometerGetCurrentReading (g), read once a second\"\n");
        m.Append("}\n");
        File.WriteAllText(Path.Combine(dir, "meta.json"), m.ToString(), new UTF8Encoding(false));
    }

    static string Describe(Skeleton body, Tuple<float, float, float, float> floor)
    {
        if (body == null) return "no person tracked";
        Func<JointType, bool> seen = j => body.Joints[j].TrackingState == JointTrackingState.Tracked;
        return string.Format(CultureInfo.InvariantCulture, "person at {0:0.0} m; head {1}; feet {2}; floor {3}",
                             body.Position.Z, seen(JointType.Head) ? "ok" : "NOT SEEN",
                             seen(JointType.FootLeft) && seen(JointType.FootRight) ? "ok" : "NOT BOTH SEEN",
                             floor.Item2 != 0 ? "ok" : "not found");
    }

    static string I(int v) { return v.ToString(CultureInfo.InvariantCulture); }
    static string L(long v) { return v.ToString(CultureInfo.InvariantCulture); }
    static string F(double v) { return v.ToString("R", CultureInfo.InvariantCulture); }
    static string Q(string s)
    {
        if (s == null) return "null";
        StringBuilder b = new StringBuilder("\"");
        foreach (char c in s)
        {
            if (c == '"' || c == '\\') b.Append('\\').Append(c);
            else if (c < ' ') b.Append("\\u").Append(((int)c).ToString("x4"));
            else b.Append(c);
        }
        return b.Append('"').ToString();
    }
}
