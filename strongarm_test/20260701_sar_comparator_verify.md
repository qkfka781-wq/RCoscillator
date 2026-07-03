# SAR StrongARM 비교기 단독검증 스펙 & 결과

**날짜**: 2026-07-01 | **공정/코너**: Samsung 28FDS, TT / 27°C / presim(기생 없음) | **DUT**: `0_BARAM/StrongARM`

## 1. 대상 정의
- **용도**: SAR ADC 비교기 — 샘플 후 두 전압을 비교해 COMP(비트 결정) 출력.
- **입력 VINP/VINN** = CDAC output = TG(transmission gate) 출력.
- **포트**: `CLK OUT OUTB VDD VINN VINP VSS` (외부 바이어스 없음). CLK high = eval(tail on), low = precharge/reset.
- **입력쌍**: lvtnfet W=160n / L=80n (nMOS 입력).
- ⚠ OSC용(osc1/osc2·refn 300m) StrongARM과 **다른 용도** — 혼동 주의.

## 2. 동작 스펙 (목표)
| 항목 | 목표 | 근거 |
|------|------|------|
| 입력 CM 범위 | 0.5 ± 0.3 V (= 0.2 ~ 0.8 V) | 사용자 지정 |
| 비교 클럭 | 50 ~ 300 MHz (샘플당 14 comparison) | 사용자 지정 |
| 입력환산 분해능 | < ½ LSB ≈ 110 µV | CDAC LSB 221 µV의 절반 |
| 오프셋 | DLF/캘루프가 제거 → **후순위** | 사용자 지정 |

## 3. 검증 방법 (buildStrongarmTB.il, 1-tran)
`strongarm_test/build_strongarm_tb.il` — CDAC와 동일 패턴(by-name 결선, vpulse CDF prompt 매칭).
- **V_CLK** vpulse 0/1, 주기 Tclk=3.33 ns (**300 MHz 최악**).
- **V_DIFF** = vpulse 삼각파 ±5 mV, PLUS=VINP MINUS=VINN → 차동만 인가. Tdiff=1.667 µs (up-ramp 250 클럭 → vdiff 40 µV 스텝).
- **V_CM** = vpulse 삼각파 0.2↔0.8, PLUS=VINN MINUS=VSS → CM 느린 스윕. Tcm=20 µs.
- 계층 Tclk ≪ Tdiff ≪ Tcm → 1-tran에 (CM, vdiff, 판정) scatter. **6001 comparison**.
- ADE: tran stop=20 µs, maxstep ≤ 0.6 ns. export `time,VINP,VINN,CLK,OUT` → `sar_comp.csv`.
- 분석: CLK 상승엣지마다 (CM=VINN, vdiff=VINP−VINN, 판정=OUT).

## 4. 결과
6001 comparison **전부 클린 판정**(metastable 0개). 폴러리티 OUT=1 ⟺ VINP>VINN.

**입력 CM 임계 실패:**

| 입력 CM | 오판율(|vdiff|>0.5mV) | 판정 |
|---------|------|------|
| ≤ 0.25 V | **~50 %** | 완전 불능 — 출력이 vdiff 부호 무관 고착 |
| 0.30 V | 8.2 % | 경계 |
| **≥ 0.35 V** | **0 %** | 정상 |

정상영역(CM ≥ 0.35 V): offset ≈ ±10 µV (= deterministic 0), 전이 밴드 < 40 µV (½LSB 110 µV보다 여유), 최악 300 MHz에서도 매 사이클 레일까지 해소. clk2Q = 154 ps (기존 presim).

## 5. 해석 & 결론
- **소자·속도·감도는 문제없음.** 오직 **저CM 실패**뿐.
- **원인**: nMOS 입력쌍 저CM 한계 — CM < ~0.33 V면 Vgs ≈ Vth → tail 전류 붕괴 → eval 창 내 차동 미형성.
- **충돌**: SAR 스펙 CM 하한 0.2 V가 실패영역에 있음.

## 6. 미해결 / 다음 판단
⭐ **실제 SAR 변환 중 비교 시점 CM이 진짜 0.2 V까지 스윙하는지 확인 필요** (top-plate charge-redistribution은 변환 중 CM 시프트). dcOp/과도에서 (VINP+VINN)/2 파형으로 판별.
- **CM이 0.5 부근 유지(진짜 차동)** → StrongARM 이대로 합격.
- **CM이 0.2까지 하강** → fix 우선순위: ① CDAC/TG 설계로 비교 CM ≥ 0.4 유지(최소변경) → ② double-tail / 상보입력(rail-to-rail) 또는 pMOS 입력 비교기.

## 7. 산출물
- TB 빌더: `strongarm_test/build_strongarm_tb.il`
- 원데이터: `strongarm_test/sar_comp.csv` (time,OUT,VINP,VINN,CLK)
