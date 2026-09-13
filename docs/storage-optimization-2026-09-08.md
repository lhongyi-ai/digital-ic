# Sensor Spectrum-Cache Reuse: One SPRAM Released

This change modifies only on-chip storage allocation and port arbitration in `upduino_sensor`. The SEN1 log format, sample rate, raw-record retention count, and spectral arithmetic remain unchanged. Synthesis and place-and-route of the complete 800 S/s sensor top confirm a reduction from four SPRAM blocks to three. The tradeoff is 41 additional packed LCs and a single-run Fmax estimate decrease from 17.33 MHz to 16.53 MHz; both versions meet the 12 MHz target. This is not a timing-speedup or measured energy-saving result.

## Change and port ownership

The original design used three `16K × 16` SPRAMs for raw logs and a fourth identical SPRAM for the 16 uint32 powers (64 B) of the most recent complete window. At the default 24,000 raw records of 4 B each, the three data RAMs provide 98,304 B, of which the raw log occupies 96,000 B.

The new design retains three RAMs and places the 64 B spectrum cache in the final 32 words of the third RAM. All internal addresses are 16-bit word addresses:

| Content | Default word addresses | Capacity |
| --- | --- | ---: |
| Raw log | `0x0000..0xBB7F` | 96,000 B |
| Unused gap | `0xBB80..0xBFDF` | 2,240 B |
| Latest spectral powers | `0xBFE0..0xBFFF` | 64 B |

`SPECTRUM_WORD_BASE = 3 × 2^BANK_ADDR_BITS − 32` is always aligned to 32 words. Startup rejects parameters that overlap raw storage and the reserved spectrum region. A configuration without spectral processing can still use all three RAMs.

When a spectral power becomes available, its low 16 bits are written first and its held high 16 bits on the next cycle. These two cycles have priority on the RAM port. If a raw record has written raw data but not its timestamp delta, the delta remains in the existing `interval_hold` register until spectral writes finish. Until then, `stored_count` does not advance and another raw record is not accepted. New sample handshakes also pause during spectral writes; calibration and spectral branches use the same handshake condition. A raw record therefore cannot be split between two record positions.

The implementation adds no data-holding registers; it reuses the existing spectrum high-half and index registers. The current DSP leaves multiple idle cycles between spectral powers. With `VIB_ASSERT`, assertions check that a new power cannot coincide with writing the previous power's high half, and that raw and spectral write addresses do not overlap. Replacing the producer with one power per cycle would require redesigned handshaking or a queue; this rate contract would no longer apply.

SEN1 still outputs spectral powers in header bytes 144..207, with unchanged raw payload and CRC layout. Export waits for raw-record, calibration, and spectral processing to finish, then reads the spectrum cache from shared RAM. With no complete window, it still outputs 16 zeros. A trailing segment shorter than 256 samples does not overwrite the last complete window.

## Actual build results under matched conditions

These are actual tool-run results, without physical-board access. Both versions use `upduino_sensor`, UP5K SG48, 12 MHz, seed 1, 800 S/s, axis 0, 480,000 target samples, 24,000 stored samples, default nominal calibration, and the same N256 single-MAC spectral algorithm and ROMs.

| Metric | Rebuilt original | Modified build | Change |
| --- | ---: | ---: | ---: |
| SPRAM / 4 | 4 | 3 | −1 block, or 32 KiB of allocated capacity |
| EBR / 30 | 9 | 9 | 0 |
| DSP / 8 | 1 | 1 | 0 |
| LUT4 | 3,781 | 3,798 | +17 |
| Packed LC / 5,280 | 4,874 | 4,915 | +41 |
| Total register cells | 1,734 | 1,734 | 0 |
| Post-route Fmax estimate | 17.3346 MHz | 16.5278 MHz | −0.8068 MHz |
| Longest synchronous path | 57.6880 ns | 60.5040 ns | +2.8160 ns |
| 12 MHz target | PASS | PASS | Met |

The released resource is allocated RAM capacity; the chip's physical capacity does not increase, and reduced power has not been demonstrated. This is a paired comparison with one seed, not a distribution across placement seeds or every PVT condition. The sensor design still uses 93.1% of LCs; a complete classifier cannot simply be added with an assumption that resources suffice.

Tools: Yosys `0.68+195 / 435977e97-dirty`, nextpnr `0.11.1-19-g8dbcee5c`, Verilator `5.051 devel / v5.050-312-gb1c06fdb0 (mod)`, and cocotb 2.1.0. `dirty` / `mod` are version strings from the installed tool distribution.

## Targeted verification

All six complete sensor-system scenarios passed with `VIB_ASSERT`, with no XML failures. All tests use RTL plus pin-level ADXL345 / SPI NOR behavioral models, not physical measurements.

| Scenario | Actual checks | Result |
| --- | --- | --- |
| nominal | 88 inputs, 80 stored records; crosses three reduced-capacity RAM banks and NOR pages; timer wrap, calibration, CRC, commit ordering, and old-log protection | PASS; complete SEN1 binary exactly matches the archived simulation log |
| overflow | Four raw records with an interval exceeding the delta representation range | PASS; overflow flag retained and complete SEN1 binary matches the archive |
| spectrum | 256 input/stored records, one complete spectral window | PASS; 16 powers match the Python integer reference and complete SEN1 binary matches the archive |
| spectrum_storage | 520 inputs, 368 stored records; simulated bank capacity 256 words, with raw data ending exactly before the spectrum reserve; two full spectral windows and an eight-sample tail | PASS; latest spectrum is from the second complete window; all raw records, deltas, CRC, and spectral powers are correct |
| spectrum_overlap | Same simulated capacity, requesting 369 stored records and thereby overlapping raw and spectral regions | PASS; startup rejected, error bit 7, zero observed samples, no sensor or Flash transactions |
| spectrum_short | Eight inputs, no complete spectral window | PASS; complete raw records and 16 zero powers, with no stale RAM leakage |

`spectrum_storage` controls sensor service timing to align a new sample read over the actual SPI interface with the first spectral power. It exercises **two cycles of delayed raw timestamp writes** and **two cycles of new-sample waiting**. It verifies both the integrity of a partially written raw record and data retention while the sample handshake is blocked. Conflicts are not manufactured by directly changing internal data or faking spectrum outputs. This scenario intentionally changes two sampling intervals to trigger arbitration; it is not a physical ADC jitter experiment.

Reduced capacity is used only to reach RAM-bank and allocation boundaries quickly. The complete default 800 S/s capacity is verified by the full-top-level P&R above. These have different evidence scopes.

## Evidence retention and reproduction

Existing `artifacts/firmware/`, `artifacts/evidence/`, models, test-set results, and old `build/sensor_*` reports were not overwritten. This run has the separate directory `build/storage-optimization-2026-09-08/`:

- `baseline/`: original RTL/test/build-script copies, source SHA256 list, and a newly executed complete build.
- `optimized/build/`: modified full synthesis, place-and-route, bitstream, and reports.
- `optimized/final-cases/`: final targeted regression with assertions enabled.
- `optimized/source-lock.json`: SHA256 values for modified RTL, spectrum ROMs, build scripts, and tests.
- `evidence-lock.json`: SHA256 list for this run's builds, XML, simulation reports, and binary logs.
- `run_isolated.py`: a thin wrapper around original build/simulation scripts that changes only output directories, without modifying default build scripts.

The original baseline was the clean local working tree at commit `72aa42f47e1c575a6b6f2d731ea06568ae9d6459`. The rebuilt baseline bitstream's SHA256 exactly matches the old archived bitstream. The table links source files to actual builds. The modified RTL assertion section is included in that build's source snapshot; synthesis did not enable `VIB_ASSERT`, while the verification regression did.

| File | Original SHA256 | Modified SHA256 |
| --- | --- | --- |
| `rtl/upduino_sensor.sv` | `3f38f408b10cc1f7a4f07ce7359ab739009b5a530e2d2b1e9446dda5ed71d092` | `0e64af7f963e80e37efa438c6fb2ff0ece0f65cc9d6ba8d5d8314112aac28d46` |
| `board.bin` | `035d79e2a98fbd0a09a4836e45d9b08bd13ebb455d81662adf3ec90ea4587472` | `01512b61f893c942d7f04bf9c61cc26aa311ebd715f6f08fb947ad54e939cfc7` |
| `report.json` | `ac7d67589d966af774b009ce8c6bc0d0f67b26423dfbcab57e166944b296000f` | `e529d330aa687a9b82f1b37a11e5299f8e35f63c48a3357f004bff11e5c98a28` |

For local reproduction of the modified results, use a new directory name to preserve this run:

```sh
source scripts/env.sh
python build/storage-optimization-2026-09-08/run_isolated.py build reproduction/build --rate 800
python build/storage-optimization-2026-09-08/run_isolated.py sim reproduction/tests --case all
```

`build/` is a locally generated directory excluded by `.gitignore`. A fresh checkout can rebuild the modified results directly with `scripts/build_sensor.py --rate 800` and `sim/run_sensor_system.py --case all`, or rebuild the original in a separate checkout at the baseline commit above. Physical programming, real sensor acquisition, noise measurements, and power measurements have not been performed.
