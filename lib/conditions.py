"""What the machine was doing when it ran: load, power source, power profile.

A busy or battery-powered laptop scores lower than it can; these are stored
next to the scores and shown with them. HB_SYS overrides /sys for tests.
"""
import os
from pathlib import Path


def sys_root():
    return Path(os.environ.get('HB_SYS') or '/sys')


def on_ac():
    """True on mains, False on battery, None when there is no supply info."""
    found = None
    for supply in (sys_root() / 'class' / 'power_supply').glob('*'):
        try:
            kind = (supply / 'type').read_text().strip()
            if kind == 'Mains':
                if (supply / 'online').read_text().strip() == '1':
                    return True
                found = False
        except OSError:
            continue
    return found


def power_profile():
    try:
        return (sys_root() / 'firmware' / 'acpi' / 'platform_profile').read_text().strip()
    except OSError:
        return None


def load1():
    if os.environ.get('HB_LOAD'):
        return float(os.environ['HB_LOAD'])
    return os.getloadavg()[0]


def snapshot():
    cores = os.cpu_count() or 1
    load = round(load1(), 2)
    return {
        'load1': load,
        'threads': cores,
        'busy': load > max(1.0, cores * 0.25),
        'ac': on_ac(),
        'power_profile': power_profile(),
    }


def warnings(c):
    out = []
    if c.get('busy'):
        out.append(f"busy: 1-minute load {c['load1']} on {c['threads']} threads; scores will be low")
    if c.get('ac') is False:
        out.append('on battery')
    if c.get('power_profile') not in (None, 'performance'):
        out.append(f"power profile {c['power_profile']}, not performance")
    return out


def has_display():
    if os.environ.get('WSL_DISTRO_NAME') or os.environ.get('SHELL_WSL') == '1':
        return False
    return bool(os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))
