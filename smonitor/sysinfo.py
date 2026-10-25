"""Read-only system data: temps, throttle, freqs, threads and core placement.

Everything here reads kernel /sys, various hwmon/thermal interfaces or psutil
stats. Important: these are all READ operations - nothing is ever written to
the chips or drivers.
"""

import glob
import os
import subprocess

import psutil

from .config import THERMAL_TYPES


def read_text(path, default=""):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


# --------------------------------------------------------------------------- #
# temperatures
# --------------------------------------------------------------------------- #
def read_temperature():
    """Return (degC, zone_name) of the CPU package or (None, None)."""
    try:
        zones = sorted(glob.glob("/sys/class/thermal/thermal_zone*"),
                       key=lambda p: int(p.rsplit("_", 1)[1]))
    except ValueError:
        zones = glob.glob("/sys/class/thermal/thermal_zone*")
    for zone in zones:
        if read_text(os.path.join(zone, "type")) in THERMAL_TYPES \
                and os.path.exists(os.path.join(zone, "temp")):
            raw = read_text(os.path.join(zone, "temp"))
            try:
                return int(raw) / 1000.0, os.path.basename(zone)
            except ValueError:
                continue
    return None, None


def read_nvme_temps():
    """Return {device: degC} for each NVMe SSD (from SMART/hwmon)."""
    out = {}
    for hw in glob.glob("/sys/class/nvme/nvme[0-9]*/device/hwmon/hwmon*"):
        raw = read_text(os.path.join(hw, "temp1_input"))
        if raw.lstrip("+-").isdigit():
            device = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(hw))))
            out[device] = int(raw) / 1000.0
    return out


def read_pch_temp():
    """Return (degC, label) for the PCH if the kernel exposes it."""
    best = None
    for hw in glob.glob("/sys/class/hwmon/hwmon*"):
        name = read_text(os.path.join(hw, "name")).lower()
        for label_file in glob.glob(os.path.join(hw, "temp*_label")):
            label = read_text(label_file).lower()
            if "pch" in label or "pch" in name:
                raw = read_text(label_file[:-len("_label")] + "_input")
                if raw.lstrip("+-").isdigit():
                    best = int(raw) / 1000.0
    if best is not None:
        return best, "PCH"
    for zone in glob.glob("/sys/class/thermal/thermal_zone*"):
        if "pch" in read_text(os.path.join(zone, "type")).lower():
            raw = read_text(os.path.join(zone, "temp"))
            if raw.lstrip("+-").isdigit():
                return int(raw) / 1000.0, "PCH(acpi)"
    return None, None


def read_ram_temp():
    """Return (degC, label) for DIMM/RAM sensors if exposed (rare on laptops)."""
    for hw in glob.glob("/sys/class/hwmon/hwmon*"):
        name = read_text(os.path.join(hw, "name")).lower()
        for label_file in glob.glob(os.path.join(hw, "temp*_label")):
            label = read_text(label_file).lower()
            if any(k in label for k in ("dimm", "ram")) or "ram" in name:
                base = label_file[:-len("_label")]
                raw = read_text(base + "_input")
                if raw.lstrip("+-").isdigit():
                    return int(raw) / 1000.0, label or "RAM"
    return None, None


def read_core_temps():
    """Return {core_index: degC} from the coretemp hwmon driver."""
    temps = {}
    for hw in glob.glob("/sys/class/hwmon/hwmon*"):
        if read_text(os.path.join(hw, "name")) != "coretemp":
            continue
        for label_file in glob.glob(os.path.join(hw, "temp*_label")):
            label = read_text(label_file)
            if label.lower().startswith("core "):
                try:
                    core = int(label.split()[-1])
                except ValueError:
                    continue
                raw = read_text(label_file[:-len("_label")] + "_input")
                if raw.lstrip("+-").isdigit():
                    temps[core] = int(raw) / 1000.0
    return temps


# --------------------------------------------------------------------------- #
# throttle + frequency
# --------------------------------------------------------------------------- #
def read_throttle():
    """Return (core_throttle_events, package_throttle_events)."""
    core = pkg = 0
    for d in glob.glob("/sys/devices/system/cpu/cpu[0-9]*/thermal_throttle"):
        v = read_text(os.path.join(d, "core_throttle_count"), "0")
        core += int(v) if v.lstrip("+-").isdigit() else 0
        v = read_text(os.path.join(d, "package_throttle_count"), "0")
        pkg += int(v) if v.lstrip("+-").isdigit() else 0
    return core, pkg


def read_freqs():
    """Return (avg_cur_khz, avg_max_khz, governor) or (None, None, None)."""
    cur, mx, gov = [], [], ""
    for d in sorted(glob.glob("/sys/devices/system/cpu/cpu[0-9]*"),
                    key=lambda p: int(p.rsplit("cpu", 1)[1])):
        fdir = os.path.join(d, "cpufreq")
        c = read_text(os.path.join(fdir, "scaling_cur_freq"))
        m = read_text(os.path.join(fdir, "scaling_max_freq"))
        if c.lstrip("+-").isdigit() and m.lstrip("+-").isdigit():
            cur.append(int(c))
            mx.append(int(m))
            if not gov:
                gov = read_text(os.path.join(fdir, "scaling_governor"))
    if cur:
        return sum(cur) / len(cur), sum(mx) / len(mx), gov
    return None, None, None


# --------------------------------------------------------------------------- #
# threads + core placement
# --------------------------------------------------------------------------- #
def _walk_processes():
    """Yield psutil.Process instances, skipping everything we can't read."""
    for p in psutil.process_iter():
        try:
            yield p
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            continue


def collect_threads():
    """Return (loadavg1, total_threads, logical_cpu_count)."""
    threads = 0
    for p in _walk_processes():
        try:
            threads += p.num_threads()
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            pass
    try:
        load1 = os.getloadavg()[0]
    except (OSError, AttributeError):
        load1 = 0.0
    return load1, threads, (psutil.cpu_count(logical=True) or 0)


def collect_core_map():
    """Return {core: [(pid, tid, comm)]} via /proc/<pid>/task/<tid>/stat."""
    per_core = {}
    for p in _walk_processes():
        try:
            pid = p.pid
            name = (p.name() or "?")[:20]
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
        base = f"/proc/{pid}/task"
        try:
            tids = os.listdir(base)
        except OSError:
            continue
        for tid in tids:
            try:
                with open(f"{base}/{tid}/stat") as fh:
                    line = fh.read()
                end = line.rfind(")")
                fields = line[end + 1:].split()
                # Linux /proc stat: 'processor' is field 39 -> token 36 after ')'.
                if len(fields) > 36 and fields[36].lstrip("+-").isdigit():
                    core = int(fields[36])
                    per_core.setdefault(core, []).append((pid, tid, name))
            except (OSError, ValueError):
                continue
    return per_core


# --------------------------------------------------------------------------- #
# desktop theme (GNOME)
# --------------------------------------------------------------------------- #
def gsettings(key):
    try:
        out = subprocess.check_output(
            ["gsettings", "get", "org.gnome.desktop.interface", key],
            stderr=subprocess.DEVNULL, timeout=2)
        return out.decode().strip().lower()
    except Exception:
        return ""


def detect_system_theme():
    """Return 'dark' or 'light' from the GNOME desktop settings."""
    if "dark" in gsettings("color-scheme"):
        return "dark"
    if "dark" in gsettings("gtk-theme"):
        return "dark"
    return "light"