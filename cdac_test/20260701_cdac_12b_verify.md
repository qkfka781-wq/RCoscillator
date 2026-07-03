# CDAC 12b 단독검증 스펙 & 결과

**날짜**: 2026-07-01 | **공정/코너**: Samsung 28FDS, TT / 27°C / presim(기생 없음) | **DUT**: `0_BARAM/CDAC_12b`

## 1. 대상 정의
- **용도**: SAR ADC의 12-bit 전하재분배 DAC (split-CDAC, Koo 2026 기반).
- **구조**: MSB 7b @ VOUT (캡 1·2·4·8·16·32·64 cu, bit5~11), LSB 5b @ VX (1·2·4·8·16 cu, bit0~4), **Bridge** 6 cu (VOUT↔VX), **Redundant** 143 cu (VX↔VSS).
- **단위 캡**: shielded CMOM 4.436 fF (finger 10×10), geometry 고정·weight는 multiplier(Nb//)만.
- **이상 전달식**: VOUT = CODE/4250 → 1 LSB = VDD/4250 = 235 µV @1V.
- **포트**: `IN<11:0> VOUT VX VDD VSS`. IN<k> → (셀 내부 INV) → bottom plate = ~IN<k>.

## 2. 동작 스펙 (목표)
| 항목 | 목표 | 근거 |
|------|------|------|
| 분해능 | 12-bit | SAR 스펙 |
| INL / DNL | < ±0.5 LSB, 단조·no missing | 12b 정적 선형성 |
| Full-scale | ≈ 0.905·VDD (redundant/bridge 감쇠) | 이상 전달식 |
| MC(mismatch) 3σ | INL/DNL < ±0.5 LSB | 후순위(resume) |

## 3. 검증 방법 (buildCdacTB.il, 1-tran counter trick)
`cdac_test/build_cdac_tb.il` — clean slate 후 DUT + 자극 + 전원 + 리셋SW를 by-name 결선.
- **전원**: VDD vdc=1, VSS=0(gnd).
- **리셋 SW ×2**(analogLib switch): VOUT↔0, VX↔0 (둘 다 floating top-plate) — RST vpwl로 [0,t_rst] 닫힘 후 영구 open. 리셋 1회면 충분(선형 charge-redist).
- **코드 자극 = 이진카운터 트릭**: IN<11:0> 12개 vpulse, bit k → delay=t_rst+2^k·Tcode, width=2^k·Tcode, period=2^(k+1)·Tcode, **V1=1/V2=0(INV 보정 → plate=정코드)**. 한 tran에 0→4095.
- **DC 불가(캡은 DC open) → tran**. stop = t_rst + 4096·Tcode.
- **⭐ Tcode = 100 ns (정착 필수)**: 10 ns면 MSB 동시전환 정착(~15–18 ns) 미달로 글리치.
- export `time, VOUT` → 각 코드창 끝(t_rst+(n+0.9)·Tcode)에서 슬라이스.

## 4. 결과 (정본: `code2_cdac.csv`, Tcode=100ns, 410µs, VSS=0)
| 항목 | 값 | 판정 |
|------|-----|------|
| Full-scale | 0.9046 V (code0 = 0 V) | 이상값 정합 ✓ |
| LSB | 220.9 µV | (이상 235 µV) |
| **INL** | **−0.199 / +0.113 LSB** (rms 0.079) | ≪ ±0.5 ✓ |
| **DNL** | **−0.057 / +0.005 LSB** (rms 0.010) | ≪ ±0.5 ✓ |
| MSB carry (2047→2048) | −0.055 LSB (타 carry −0.058과 동일) | ✓ |
| 단조성 / missing code | 완전 단조 / 0 | ✓ |

## 5. 해석 & 결론
- **12b급 정적 선형성 확정.** bridge 6 / redundant 143 정합비(=32) 포팅이 정확히 맞음.
- **정착 아티팩트 규명**: Tcode=10 ns run(`code_cdac.csv`)은 MSB carry(2047→2048, 3071→3072)에서 ±95 LSB·비단조 → 파형상 MSB 에지에서 −206 mV kickback이 ~15 ns에 정착, 10 ns 창은 샘플이 과도구간에 걸림. **정적 오차 아님.** 100 ns 창에서 완전 소멸(위 표).
- **부수 소득**: **MSB DAC 정착 ≈ 15–18 ns** → SAR MSB 비트사이클 하한(딜레이라인 SAR clk 설계 제약).
- (초기 run VSS=1 실수 → +1V 오프셋, 선형성 동일. VSS=0 재실행으로 확정.)

## 6. 미해결 / 다음
⭐ **Monte Carlo (mismatch)** = resume 지점 — 4.436 fF unit이 12b 매칭에 충분한지(3σ INL/DNL < ±0.5 LSB?). ADE Assembler, Sampling=LDS, Mismatch only, 100~200 pt, PDK statistics section 필요. 부족 시 unit 캡 ↑(σ ∝ 1/√area).

## 7. 산출물
- TB 빌더: `cdac_test/build_cdac_tb.il`, 코드소스 생성기 `cdac_test/make_code_sources.il`
- 배치 가이드: `cdac_test/schematic_setup.md`, `cdac_test/README.md`
- 원데이터: `cdac_test/code2_cdac.csv`(정본 100ns), `cdac_test/code_cdac.csv`(10ns, 글리치 참고)
- 분석 결과: `cdac_test/cdac_transfer_summary.csv`(code,VOUT,INL,DNL), `cdac_test/cdac_inl_dnl.png`
