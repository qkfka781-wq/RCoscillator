# Requested CSV Window Numeric Table

Window: `32.5 us` to `41.5 us` from `top/top_run.csv`.

## Interpretation

| Signal | Interpretation |
|---|---|
| `CP1_u12`, `CP2_u12` | unsigned 12-bit digital CP hold codes |
| `DD1_u12`, `DD2_u12` | unsigned 12-bit sampled ADC/DLF codes |
| `DIFF_SAMPLE_s12`, `DIFF_s12` | signed 12-bit two's-complement values |
| `D_u17` | offset-binary unsigned 17-bit D code, mid code = 65536 |
| `D_minus_mid_s17` | signed correction amount, `D_u17 - 65536` |
| `oref_V` | analog voltage corresponding to the D/oref actuator state |

## CP Analog Voltage To Digital Code Mapping

This table maps the analog phase difference to the CP digital code at `DATA_OUT` rising edges.
The CSV register trace shows `CP1 -> DD2` and `CP2 -> DD1` at the following DLF sample.

| Rule | Analog source | Digital code | DATA_OUT mapping |
|---|---|---|---|
| `CLK_OSC = 0` | `osc1 - osc2` | `CP1_u12` unsigned 12b | `DD2_from_CP1_u12` |
| `CLK_OSC = 1` | `osc11 - osc22` | `CP2_u12` unsigned 12b | `DD1_from_CP2_u12` |

| event | DATA_OUT_t_us | CLK_OSC | analog_source | analog_voltage_V | CP_code_signal | CP_code_u12 | mapped_DD_signal | mapped_DD_u12 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 | 32.792 | 0 | osc1 - osc2 | 0.000381 | CP1_u12 | 2112 | DD2_from_CP1_u12 | 2112 |
| 15 | 35.103 | 1 | osc11 - osc22 | 0.000422 | CP2_u12 | 1970 | DD1_from_CP2_u12 | 1970 |
| 16 | 37.381 | 0 | osc1 - osc2 | 0.000050 | CP1_u12 | 2105 | DD2_from_CP1_u12 | 2105 |
| 17 | 39.683 | 1 | osc11 - osc22 | 0.000194 | CP2_u12 | 1982 | DD1_from_CP2_u12 | 1982 |

## Active CP To Next DLF Register Mapping

Each active CP hold is checked against the following DLF sample register value.

| hold_event | DATA_OUT_t_us | CLK_OSC | active_CP | CP_u12 | next_DLF_event | next_DLF_t_us | mapped_DD | DLF_DD_u12 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 | 32.792 | 0 | CP1_u12 | 2112 | 8 | 35.129 | DD2_u12 | 2112 |
| 15 | 35.103 | 1 | CP2_u12 | 1970 | 8 | 35.129 | DD1_u12 | 1970 |
| 16 | 37.381 | 0 | CP1_u12 | 2105 | 9 | 39.709 | DD2_u12 | 2105 |
| 17 | 39.683 | 1 | CP2_u12 | 1982 | 9 | 39.709 | DD1_u12 | 1982 |

## DLF Update Samples

`DIFF_s12` follows the opposite sign of `DD2-DD1` here because `DREF=0`, so `DIFF_s12 = -(DD2-DD1)`. `DIFF_SAMPLE_s12` stores the sampled `DD2-DD1` value before that sign inversion.

| event | t_us | CP1_u12 | CP2_u12 | DD1_u12 | DD2_u12 | DD2-DD1 | DIFF_SAMPLE_s12 | DIFF_s12 | D_u17 | D_minus_mid_s17 | oref_V |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | 35.129 | 2048 | 2048 | 1970 | 2112 | 142 | 142 | -142 | 64405 | -1131 | 0.504597 |
| 9 | 39.709 | 2048 | 2048 | 1982 | 2105 | 123 | 123 | -123 | 64675 | -861 | 0.503193 |

## DATA_OUT Hold Samples

| event | t_us | CP1_u12 | CP2_u12 | CP2-CP1 | DD1_u12 | DD2_u12 | oref_V |
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
