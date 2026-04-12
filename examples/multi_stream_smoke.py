#!/usr/bin/env python3
"""Live 2-channel smoke test for MultiStream against bee3-status.local.

Provisions two USB channels (FT8 + WSPR @ 20m) that share one multicast
group, runs MultiStream for ~20s, and prints per-SSRC packet/sample counts.

Success = both callbacks fire with non-zero samples and reasonable
completeness; no "unknown SSRC" warnings for our two SSRCs.
"""

import argparse
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from ka9q import MultiStream, RadiodControl, StreamQuality

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("multi_smoke")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="bee3-status.local")
    ap.add_argument("--duration", type=float, default=20.0)
    ap.add_argument("--preset", default="usb")
    ap.add_argument("--sample-rate", type=int, default=12000)
    ap.add_argument("--encoding", type=int, default=2, help="S16BE=2")
    args = ap.parse_args()

    freqs = {
        "FT8-20m": 14.074e6,
        "WSPR-20m": 14.0956e6,
    }

    stats = defaultdict(lambda: {"callbacks": 0, "samples": 0, "gaps": 0, "rms": 0.0})

    def make_cb(label):
        def cb(samples: np.ndarray, q: StreamQuality):
            s = stats[label]
            s["callbacks"] += 1
            s["samples"] += len(samples)
            s["gaps"] += len(q.batch_gaps)
            s["rms"] = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
        return cb

    log.info(f"Connecting to {args.host}")
    with RadiodControl(args.host) as control:
        multi = MultiStream(control=control)

        infos = {}
        for label, fhz in freqs.items():
            info = multi.add_channel(
                frequency_hz=fhz,
                preset=args.preset,
                sample_rate=args.sample_rate,
                encoding=args.encoding,
                on_samples=make_cb(label),
            )
            infos[label] = info
            log.info(
                f"  {label}: {fhz/1e6:.4f} MHz SSRC={info.ssrc} "
                f"{info.multicast_address}:{info.port}"
            )

        addrs = {(i.multicast_address, i.port) for i in infos.values()}
        if len(addrs) != 1:
            log.error(f"Channels did not share a multicast group: {addrs}")
            return 2

        multi.start()
        log.info(f"Running for {args.duration:.0f}s ...")
        try:
            time.sleep(args.duration)
        except KeyboardInterrupt:
            pass
        multi.stop()

    print("\n=== Per-channel results ===")
    ok = True
    for label in freqs:
        s = stats[label]
        exp = args.duration * args.sample_rate
        pct = 100.0 * s["samples"] / exp if exp else 0.0
        print(
            f"  {label:10s}  cbs={s['callbacks']:4d}  "
            f"samples={s['samples']:>7d}  ({pct:5.1f}% of {int(exp)})  "
            f"gaps={s['gaps']}  rms={s['rms']:.4f}"
        )
        if s["callbacks"] == 0 or s["samples"] == 0:
            ok = False
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
