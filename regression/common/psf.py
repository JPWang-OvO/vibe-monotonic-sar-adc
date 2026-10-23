"""Read real/complex named PSF ASCII traces on the execution host."""
import bisect
import re


def read_psf(path, axis="time"):
    names, groups, values, traces, sweep = [], {}, {}, {}, []
    section, group, in_property = None, None, False
    quoted = re.compile(r'^"([^"]+)"\s+(.+)$')
    with open(path, encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if line in ("HEADER", "TYPE", "SWEEP", "TRACE", "VALUE", "END"):
                section = line
                if line == "END":
                    break
                continue
            match = quoted.match(line)
            if section == "TRACE":
                if in_property:
                    if line == ")":
                        in_property = False
                    continue
                if not match:
                    continue
                name, tail = match.groups()
                if tail.startswith("GROUP "):
                    group = name
                    continue
                if not tail.startswith('"') or name in traces:
                    raise ValueError("Unsupported PSF trace: " + line)
                names.append(name)
                traces[name] = []
                if group is not None:
                    groups[group], group = name, None
                in_property = "PROP(" in tail
            elif section == "VALUE" and match:
                key, raw = match.groups()
                if raw.startswith("("):
                    real, imag = raw.strip("()").split()
                    value = complex(float(real), float(imag))
                else:
                    value = float(raw)
                if key == axis:
                    if sweep:
                        for name in names:
                            traces[name].append(values[name])
                    sweep.append(value)
                else:
                    values[groups.get(key, key)] = value
    if sweep:
        for name in names:
            traces[name].append(values[name])
    if not sweep or any(b <= a for a, b in zip(sweep, sweep[1:])):
        raise ValueError("Missing or unordered sweep axis: " + axis)
    traces[axis] = sweep
    return traces


def interpolate(x, y, point):
    if not x[0] <= point <= x[-1]:
        raise ValueError("Measurement outside waveform")
    i = bisect.bisect_left(x, point)
    if i == 0 or x[i] == point:
        return y[i]
    fraction = (point - x[i-1]) / (x[i] - x[i-1])
    return y[i-1] + fraction * (y[i] - y[i-1])
