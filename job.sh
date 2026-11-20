#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
set -eu
cd /work
python collect.py --out-dir /out/data --start 2022-01 --end 2026-10 --pages 3 2> /out/collect-log.txt
python analyze.py --in-dir /out/data --out-dir /out/data | tee /out/report.txt
cp PREREG.md /out/PREREG.md
