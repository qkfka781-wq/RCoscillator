# Requested CSV Window Numeric Table

Window: `32.5 us` to `41.5 us` from `top/top_run.csv`.

## Interpretation

| Signal | Interpretation |
|---|---|
| `CP1`, `CP2` | 12-bit unsigned digital CP hold codes, 0 to 4095 |
| `DD1`, `DD2` | 12-bit unsigned sampled ADC/DLF codes, 0 to 4095 |
| `DIFF_SAMPLE`, `DIFF` | signed 12-bit values |
| `D code` | 17-bit offset-binary code, mid code = 65536 |
| `D - 65536` | signed correction amount represented by the D code |
| `oref` | analog voltage corresponding to the D/oref actuator state |

## CP Analog Voltage To Digital Code Mapping

This table maps the clock-edge oscillator difference to the CP digital code captured at the following `DATA_OUT` rising edge.
The CSV register trace shows `CP1 -> DD2` and `CP2 -> DD1` at the following DLF sample.

| Rule | Analog source | Digital code | DATA_OUT mapping |
|---|---|---|---|
| `CLK_OSC = 0` | `osc1 - osc2` | `CP1 code` (12-bit unsigned) | `DD2 code` from CP1 |
| `CLK_OSC = 1` | `osc11 - osc22` | `CP2 code` (12-bit unsigned) | `DD1 code` from CP2 |

| event | CLK edge (us) | CLK_OSC | analog source | edge osc diff (mV) | CP signal | CP code | mapped DD | DD code |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 | 32.650 | 0 | osc1 - osc2 | 29.081 | CP1 | 2112 | DD2 from CP1 | 2112 |
| 15 | 34.951 | 1 | osc11 - osc22 | -34.081 | CP2 | 1970 | DD1 from CP2 | 1970 |
| 16 | 37.240 | 0 | osc1 - osc2 | 25.231 | CP1 | 2105 | DD2 from CP1 | 2105 |
| 17 | 39.532 | 1 | osc11 - osc22 | -28.951 | CP2 | 1982 | DD1 from CP2 | 1982 |

## Active CP To Next DLF Register Mapping

Each active CP hold is checked against the following DLF sample register value.

| hold event | DATA_OUT (us) | CLK_OSC | active CP | CP code | next DLF event | next DLF time (us) | mapped DD | DLF DD code |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 | 32.792 | 0 | CP1 | 2112 | 8 | 35.129 | DD2 | 2112 |
| 15 | 35.103 | 1 | CP2 | 1970 | 8 | 35.129 | DD1 | 1970 |
| 16 | 37.381 | 0 | CP1 | 2105 | 9 | 39.709 | DD2 | 2105 |
| 17 | 39.683 | 1 | CP2 | 1982 | 9 | 39.709 | DD1 | 1982 |

## DLF Update Samples

`DIFF` follows the opposite sign of `DD2-DD1` here because `DREF=0`, so `DIFF = -(DD2-DD1)`. `DIFF_SAMPLE` stores the sampled `DD2-DD1` value before that sign inversion.

| event | time (us) | CP1 code | CP2 code | DD1 code | DD2 code | DD2-DD1 | DIFF_SAMPLE | DIFF | D code | D - 65536 | oref (V) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7 | 30.532 | 2048 | 2048 | 1958 | 2122 | 164 | 164 | -164 | 64097 | -1439 | 0.506312 |
| 8 | 35.129 | 2048 | 2048 | 1970 | 2112 | 142 | 142 | -142 | 64405 | -1131 | 0.504597 |
| 9 | 39.709 | 2048 | 2048 | 1982 | 2105 | 123 | 123 | -123 | 64675 | -861 | 0.503193 |

## DATA_OUT Hold Samples

| event | time (us) | CP1 code | CP2 code | CP2-CP1 | DD1 code | DD2 code | oref (V) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 | 32.792 | 2112 | 2048 | -64 | 1958 | 2122 | 0.486590 |
| 15 | 35.103 | 2048 | 1970 | -78 | 1958 | 2112 | 0.506722 |
| 16 | 37.381 | 2105 | 2048 | -57 | 1970 | 2112 | 0.489124 |
| 17 | 39.683 | 2048 | 1982 | -66 | 1970 | 2105 | 0.505061 |

## CLK_OSC Rising Edge Frequency

| edge | t_us | period_us | freq_kHz |
| ---: | ---: | ---: | ---: |
| 0 | 34.951 | 4.596 | 217.581 |
| 1 | 39.532 | 4.581 | 218.293 |
