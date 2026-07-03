# Requested CSV Window Numeric Table

Window: `32.5 us` to `41.5 us` from `top/top_run.csv`.

## Interpretation

| Signal | Interpretation |
|---|---|
| `CP1_u12`, `CP2_u12` | unsigned 12-bit digital CP hold codes |
| `DD1_u12`, `DD2_u12` | unsigned 12-bit sampled ADC/DLF codes |
| `DIFF_SAMPLE_s12`, `DIFF_s12` | signed 12-bit two's-complement values |
| `D_s17` | signed 17-bit D code interpretation |
| `oref_V` | analog voltage corresponding to the D/oref actuator state |

## DLF Update Samples

| event | t_us | CP1_u12 | CP2_u12 | DD1_u12 | DD2_u12 | DD2-DD1 | DIFF_SAMPLE_s12 | DIFF_s12 | D_s17 | oref_V |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | 35.129 | 2048 | 2048 | 1970 | 2112 | 142 | 142 | -142 | 64405 | 0.504597 |
| 9 | 39.709 | 2048 | 2048 | 1982 | 2105 | 123 | 123 | -123 | 64675 | 0.503193 |

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
