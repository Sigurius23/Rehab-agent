---
type: "decision"
title: "Which IMU trackers to buy for the first real sensor test"
status: "open"
area: "suit"
blocks:
  - "[[suit-slimevr-validation]]"
question: "Buy a Movella (Xsens) DOT 5-sensor set for the first real sensor test, with two single sensors for the feet if the ankle is wanted, and test SlimeVR trackers against it later?"
source: "simulated-sensor tests of 2026-11-16 and 2026-11-17; shop listings checked 2026-11-17"
updated: "2026-11-17"
---
# Which IMU trackers to buy for the first real sensor test

**Why trackers.** On LabValidation, one camera plus simulated orientation sensors on the pelvis, thighs and shanks brought pelvis tilt, hip and knee within their limits (4.5°, 5.8°, 5.2°), against 19-35° for the camera alone ([[t-kin-camera-plus-imu-sim]], [[t-kin-camera-plus-imu-sim-shanks]]). That is a simulated upper bound: the sensors were computed from the same motion capture the result was compared with. The camera cannot supply the ankle: its foot error is both an offset and a variable part, so the ankle needs foot sensors or stays unknown. Only real sensors can test the design.

**Recommendation: Movella (Xsens) DOT for the validation session, SlimeVR later as the product candidate.** The first test needs orientation data that can be trusted, recorded and aligned with the phones, not cheap VR tracking.

| | Movella (Xsens) DOT | SlimeVR (ICM-45686 trackers) |
|---|---|---|
| List price, checked 2026-11-17 | $750 for the 5-sensor set with charger; $132 for a single sensor (Movella's shop). Resellers list more | About $40-60 per tracker; marketplace sets of 6-10 at about $390-580 |
| Role here | The first real sensor test | Tested later against the DOTs, as the cheap candidate for the suit |
| Data | Records on the sensor, with sync between sensors; exported files | Streams to a PC over Wi-Fi; no logging on the sensor |
| Heading | | The official trackers run without a magnetometer (6-DOF), so heading drifts |
| Use in biomechanics | A research sensor, widely used in studies | Built for VR; not validated for biomechanics. Marketplace sets are clones with unknown firmware |
| Fit with this pipeline | OpenSim's OpenSense reads Xsens data; the DOT exporter's CSV needs a small conversion | Data access through the SlimeVR server, to be checked |

- **Five sensors** cover the tested design: pelvis, both thighs and both shanks. Two more on the feet only if the ankle is wanted. Five DOTs plus two singles is about $1,000 at list price.
- **To confirm with Movella before buying:** a reseller says research or commercial use of the SDK needs a separate licence, while Movella's set page lists the SDK as included. It matters for [[d-commercial-route]].
- Prices are list prices from the shops' and marketplaces' own pages, not quotes, and change; check them before ordering. Nothing has been bought and nobody has been contacted.

**The first session it enables:** two phones on OpenCap's validated setup as the reference, one phone, the trackers and the printed sole, recorded on Windows ([[build-windows]]).

## Sources

- [Movella / Xsens DOT sensor (shop)](https://shop.movella.com/us/product-lines/wearables/products/movella-dot-sensor)
- [Movella / Xsens DOT set (shop)](https://shop.movella.com/us/product-lines/wearables/products/xsens-dot-set)
- [Unbound XR, DOT set reseller listing](https://unboundxr.com/movella-xsens-dot-set-5-sensors-incl-charger)
- [Xsens software downloads](https://www.xsens.com/support/software-documentation)
- [SlimeVR docs, IMU comparison](https://docs.slimevr.dev/diy/imu-comparison.html)
- [eBay, SlimeVR-compatible 8-tracker set](https://www.ebay.com/itm/157760350485)
- [Etsy, SlimeVR trackers](https://www.etsy.com/market/vrchat_slimevr_trackers)
