// Compile-check stub of the Kinect for Windows SDK 1.8 managed API (Microsoft.Kinect.dll), NOT the SDK.
//
// It declares only the members KinectCapture.cs uses, with the signatures the tool assumes, so the tool can
// be built and run where the SDK cannot be installed (tests/test_units.py builds both with Mono's mcs).
// Every public member here is an assumption about the real SDK; the real check is build.cmd on Windows,
// which compiles against the installed Microsoft.Kinect.dll and fails before anything is recorded.
//
// With REHABTWIN_FAKE_KINECT=1 the stub reports one fake sensor that streams synthetic frames, so the
// recorder's files can be checked against rehabtwin/kinect.py. The fake's geometry (FakeScene) is a test
// fixture, not a model of the real sensor.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Threading;

namespace Microsoft.Kinect
{
    public enum KinectStatus { Undefined, Disconnected, Connected, Initializing, Error, NotPowered, NotReady,
                               DeviceNotGenuine, DeviceNotSupported, InsufficientBandwidth }
    public enum ColorImageFormat { Undefined, RgbResolution640x480Fps30, RgbResolution1280x960Fps12 }
    public enum DepthImageFormat { Undefined, Resolution640x480Fps30, Resolution320x240Fps30, Resolution80x60Fps30 }
    public enum SkeletonTrackingState { NotTracked, PositionOnly, Tracked }
    public enum JointTrackingState { NotTracked, Inferred, Tracked }
    public enum JointType { HipCenter, Spine, ShoulderCenter, Head, ShoulderLeft, ElbowLeft, WristLeft, HandLeft,
                            ShoulderRight, ElbowRight, WristRight, HandRight, HipLeft, KneeLeft, AnkleLeft, FootLeft,
                            HipRight, KneeRight, AnkleRight, FootRight }

    public struct SkeletonPoint { public float X { get; set; } public float Y { get; set; } public float Z { get; set; } }
    public struct ColorImagePoint { public int X { get; set; } public int Y { get; set; } }
    public struct Vector4 { public float X { get; set; } public float Y { get; set; } public float Z { get; set; } public float W { get; set; } }
    public struct DepthImagePixel
    {
        public short Depth { get; set; }
        public short PlayerIndex { get; set; }
        public bool IsKnownDepth { get { return Depth > 0; } }
    }

    public struct Joint
    {
        public JointType JointType { get; internal set; }
        public SkeletonPoint Position { get; set; }
        public JointTrackingState TrackingState { get; set; }
    }

    public class JointCollection : IEnumerable<Joint>
    {
        readonly Joint[] joints = new Joint[20];
        public Joint this[JointType jointType] { get { return joints[(int)jointType]; } set { joints[(int)jointType] = value; } }
        public int Count { get { return joints.Length; } }
        public IEnumerator<Joint> GetEnumerator() { return ((IEnumerable<Joint>)joints).GetEnumerator(); }
        IEnumerator IEnumerable.GetEnumerator() { return GetEnumerator(); }
    }

    public class Skeleton
    {
        public Skeleton() { Joints = new JointCollection(); }
        public JointCollection Joints { get; set; }
        public SkeletonTrackingState TrackingState { get; set; }
        public SkeletonPoint Position { get; set; }
        public int TrackingId { get; set; }
    }

    public abstract class ImageFrame : IDisposable
    {
        internal int frameNumber;
        internal long timestamp;
        public int FrameNumber { get { return frameNumber; } }
        public long Timestamp { get { return timestamp; } }
        public int Width { get { return 640; } }
        public int Height { get { return 480; } }
        public abstract int PixelDataLength { get; }
        public int BytesPerPixel { get { return 4; } }
        public void Dispose() { }
    }

    public sealed class ColorImageFrame : ImageFrame
    {
        internal byte[] bgra;
        public ColorImageFormat Format { get { return ColorImageFormat.RgbResolution640x480Fps30; } }
        public override int PixelDataLength { get { return bgra.Length; } }
        public void CopyPixelDataTo(byte[] pixelData) { Buffer.BlockCopy(bgra, 0, pixelData, 0, bgra.Length); }
    }

    public sealed class DepthImageFrame : ImageFrame
    {
        internal DepthImagePixel[] pixels;
        public DepthImageFormat Format { get { return DepthImageFormat.Resolution640x480Fps30; } }
        public override int PixelDataLength { get { return pixels.Length; } }
        public void CopyDepthImagePixelDataTo(DepthImagePixel[] pixelData) { Array.Copy(pixels, pixelData, pixels.Length); }
    }

    public sealed class SkeletonFrame : IDisposable
    {
        internal Skeleton[] skeletons;
        internal Tuple<float, float, float, float> floor;
        public int FrameNumber { get; internal set; }
        public long Timestamp { get; internal set; }
        public int SkeletonArrayLength { get { return skeletons.Length; } }
        public Tuple<float, float, float, float> FloorClipPlane { get { return floor; } }
        public void CopySkeletonDataTo(Skeleton[] skeletonData) { Array.Copy(skeletons, skeletonData, skeletons.Length); }
        public void Dispose() { }
    }

    public class AllFramesReadyEventArgs : EventArgs
    {
        internal ColorImageFrame colour;
        internal DepthImageFrame depth;
        internal SkeletonFrame skeleton;
        public ColorImageFrame OpenColorImageFrame() { return colour; }
        public DepthImageFrame OpenDepthImageFrame() { return depth; }
        public SkeletonFrame OpenSkeletonFrame() { return skeleton; }
    }

    public sealed class ColorImageStream { public void Enable(ColorImageFormat format) { } }
    public sealed class DepthImageStream { public void Enable(DepthImageFormat format) { } }
    public sealed class SkeletonStream { public void Enable() { } }

    public sealed class CoordinateMapper
    {
        public void MapDepthFrameToColorFrame(DepthImageFormat depthImageFormat, DepthImagePixel[] depthPixels,
                                              ColorImageFormat colorImageFormat, ColorImagePoint[] colorPoints)
        {
            for (int i = 0; i < depthPixels.Length; i++)
                colorPoints[i] = new ColorImagePoint { X = i % 640 + FakeScene.ShiftPx, Y = i / 640 };
        }

        public ColorImagePoint MapSkeletonPointToColorPoint(SkeletonPoint p, ColorImageFormat colorImageFormat)
        {
            return new ColorImagePoint { X = (int)Math.Round(320 - FakeScene.FocalPx * p.X / p.Z),
                                         Y = (int)Math.Round(240 - FakeScene.FocalPx * p.Y / p.Z) };
        }
    }

    public sealed class KinectSensorCollection : ReadOnlyCollection<KinectSensor>
    {
        public KinectSensorCollection(IList<KinectSensor> sensors) : base(sensors) { }
    }

    public sealed class KinectSensor
    {
        static readonly KinectSensor fake = new KinectSensor();
        Timer timer;
        int frame;
        public static KinectSensorCollection KinectSensors
        {
            get
            {
                List<KinectSensor> l = new List<KinectSensor>();
                if (Environment.GetEnvironmentVariable("REHABTWIN_FAKE_KINECT") == "1") l.Add(fake);
                return new KinectSensorCollection(l);
            }
        }
        public KinectStatus Status { get { return KinectStatus.Connected; } }
        public ColorImageStream ColorStream { get { return new ColorImageStream(); } }
        public DepthImageStream DepthStream { get { return new DepthImageStream(); } }
        public SkeletonStream SkeletonStream { get { return new SkeletonStream(); } }
        public CoordinateMapper CoordinateMapper { get { return new CoordinateMapper(); } }
        public string UniqueKinectId { get { return "FAKE-0001"; } }
        public string DeviceConnectionId { get { return "USB\\FAKE"; } }
        public int ElevationAngle { get { return 4; } set { } }
        public event EventHandler<AllFramesReadyEventArgs> AllFramesReady;
        public void Start() { timer = new Timer(Tick, null, 0, 33); }
        public void Stop() { if (timer != null) { timer.Dispose(); timer = null; } }
        public Vector4 AccelerometerGetCurrentReading() { return new Vector4 { X = 0f, Y = -1f, Z = 0f, W = 0f }; }

        void Tick(object state)
        {
            // Timer callbacks overlap when a frame takes longer than 33 ms: number the frame inside the lock, so
            // frames arrive in order as the SDK delivers them.
            lock (this)
            {
                int n = frame++;
                if (n % 10 == 7) return;                  // the sensor occasionally misses a frame
                EventHandler<AllFramesReadyEventArgs> h = AllFramesReady;
                if (h != null) h(this, FakeScene.Frames(n));
            }
        }
    }

    static class FakeScene
    {
        public const int ShiftPx = 8;                     // depth -> colour registration: 8 px to the right
        public const double FocalPx = 531.15;

        public static AllFramesReadyEventArgs Frames(int n)
        {
            byte[] bgra = new byte[640 * 480 * 4];
            byte level = (byte)(40 + (n * 37) % 180);     // frame id, survives JPEG as a flat block
            for (int y = 0; y < 480; y++)
                for (int x = 0; x < 640; x++)
                {
                    int k = (y * 640 + x) * 4;
                    bool block = x < 64 && y < 64;
                    bgra[k] = block ? level : (byte)x; bgra[k + 1] = block ? level : (byte)y; bgra[k + 2] = block ? level : (byte)128;
                }
            DepthImagePixel[] px = new DepthImagePixel[640 * 480];
            for (int y = 0; y < 480; y++)
                for (int x = 0; x < 640; x++)
                {
                    bool person = x >= 280 && x < 360 && y >= 100;
                    short d = (short)(x < 4 ? 0 : person ? 2500 : 3000);   // left edge unknown
                    px[y * 640 + x] = new DepthImagePixel { Depth = d, PlayerIndex = (short)(person ? 1 : 0) };
                }
            Skeleton body = new Skeleton { TrackingState = SkeletonTrackingState.Tracked, TrackingId = 7,
                                           Position = new SkeletonPoint { X = 0f, Y = 0f, Z = 2.5f } };
            foreach (JointType j in Enum.GetValues(typeof(JointType)))
                body.Joints[j] = new Joint { JointType = j, TrackingState = JointTrackingState.Tracked,
                                             Position = new SkeletonPoint { X = 0.1f * ((int)j % 3 - 1), Y = 0.8f - 0.08f * (int)j, Z = 2.5f } };
            Skeleton[] all = new Skeleton[6];
            all[0] = body;
            for (int i = 1; i < 6; i++) all[i] = new Skeleton();
            return new AllFramesReadyEventArgs {
                colour = new ColorImageFrame { frameNumber = n, timestamp = 33L * n, bgra = bgra },
                depth = new DepthImageFrame { frameNumber = n, timestamp = 33L * n + 2, pixels = px },
                skeleton = new SkeletonFrame { FrameNumber = n, Timestamp = 33L * n, skeletons = all,
                                               floor = Tuple.Create(0f, 0.98f, -0.2f, 0.85f) } };
        }
    }
}
