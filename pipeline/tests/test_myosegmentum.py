"""adapters/myosegmentum.py on a tiny synthetic scan: real geometry from the DICOM, overlapping slices counted once.

No MyoSegmenTUM data: the files are written here in the formats the database uses.
"""
import importlib.util
import struct
import zipfile
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location("myoseg", Path(__file__).resolve().parents[1] / "adapters" / "myosegmentum.py")
ms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ms)


def _mha(mask, z_offset):
    """A MetaImage the way the database writes them: 1 mm spacing claimed whatever the scan's real one."""
    nz, ny, nx = mask.shape
    head = (f"ObjectType = Image\nNDims = 3\nOffset = 0 0 {z_offset}\nTransformMatrix = 1 0 0 0 1 0 0 0 1\n"
            f"ElementSpacing = 1 1 1\nDimSize = {nx} {ny} {nz}\nElementType = MET_UCHAR\nElementDataFile = LOCAL\n")
    return head.encode() + mask.astype(np.uint8).tobytes()


def _ds(tag, value):
    v = value.encode()
    v += b" " * (len(v) % 2)
    return tag + b"DS" + struct.pack("<H", len(v)) + v


def _dicom(pixel_mm, slice_mm):
    return b"\0" * 132 + _ds(b"\x28\x00\x30\x00", f"{pixel_mm}\\{pixel_mm}") + _ds(b"\x18\x00\x88\x00", str(slice_mm))


def _nifti(img):
    nz, ny, nx = img.shape
    h = bytearray(352)
    h[0:4] = struct.pack("<i", 348)
    h[40:56] = struct.pack("<8h", 3, nx, ny, nz, 1, 1, 1, 1)
    h[70:72] = struct.pack("<h", 16)
    h[108:112] = struct.pack("<f", 352.0)
    h[112:120] = struct.pack("<2f", 1.0, 0.0)
    return bytes(h) + img.astype("<f4").tobytes()


def test_volumes_use_the_scanners_geometry_and_count_overlap_once(tmp_path):
    shape = (6, 10, 10)
    m1, m2 = np.zeros(shape), np.zeros(shape)
    m1[:, 2:6, 2:6] = 1                     # 16 px per slice, slices 0-5 of stack 1
    m2[:, 2:6, 2:6] = 1                     # stack 2: its top two slices are stack 1's bottom two
    ff = np.full(shape, 5.0)                # PDFF image in percent
    z = tmp_path / "S_1.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for k, (mask, z0, px) in enumerate(((m1, 0.0, 0.8), (m2, -16.0, 0.9)), start=1):
            zf.writestr(f"S_1/ImageData/S_1_FATFRACTION/S_1_FATFRACTION_stack{k}.dcm", _dicom(px, 4.0))
            zf.writestr(f"S_1/ImageData/S_1_FATFRACTION/S_1_FATFRACTION_stack{k}.nii", _nifti(ff))
            for side in ("R", "L"):
                zf.writestr(f"S_1/SegmentationMasks/S_1_stack{k}_{side}_QF.mha", _mha(mask, z0))
    v = ms.scan_volumes(z)["R"]["QF"]
    # stack 1: 6 slices at 0.8 mm pixels; stack 2 adds the 4 slices below z = 0 that stack 1 lacks, at 0.9 mm
    expect = (6 * 16 * 0.8 ** 2 + 4 * 16 * 0.9 ** 2) * 4.0 / 1000
    assert v["slices"] == 10 and v["volume_cm3"] == pytest.approx(expect) and v["pdff"] == pytest.approx(0.05)
    assert ms.dicom_geometry(_dicom(0.81875, 4)) == ((0.81875, 0.81875), 4.0)
    with pytest.raises(ValueError, match="PixelSpacing"):
        ms.dicom_geometry(b"\0" * 200)


def test_tables_parse_with_decimal_commas_and_stack_rows(tmp_path):
    (tmp_path / "Table1.csv").write_bytes("Subject ID;Gender;Age;Weight [kg];Height [cm];Disease;R_QF_strength measurement 60\xb0 [Nm];"
                                          "R_QF_strength measurement 90\xb0 [Nm];L_QF_strength measurement 90\xb0 [Nm]\n"
                                          "HV001;m;30;99;179;;369;323;\nP001;m;52;95;181;DM2;;;\n".encode("latin-1"))
    (tmp_path / "Table2.csv").write_text("Subject ID;R_QF_PDFF_mean;R_QF_PDFF_SD;R_QF_V [mm3]\nHV001_1;;;\n"
                                         "stack1;3,00;1,0;1000000,00\nstack2;5,00;1,0;3000000,00\n")
    s = ms.read_subjects(tmp_path / "Table1.csv")
    assert s["HV001"]["height_m"] == 1.79 and s["HV001"]["strength_Nm"] == {"R60": 369.0, "R90": 323.0}
    assert s["P001"]["disease"] == "DM2" and s["P001"]["strength_Nm"] == {}
    qf = ms.read_scans(tmp_path / "Table2.csv")["HV001_1"]["R"]["QF"]
    assert qf["volume_cm3"] == 4000 and qf["pdff"] == pytest.approx(0.045)          # volume-weighted
