# CDAC_12b 개별 검증 (SF28)

블록테스트 1/4. [[project_cdac_12b_design]] 의 SF28 포팅본을 고립 검증.
TB는 ADE에서 직접(see feedback_explain_sim_not_build). 여긴 결과 CSV + 분석.

## 0. 어느 넷리스트?
- **netlistafter 의 CDAC_12b 사용** (bridge C12=6, redundant C13=143 → 기생보정본).
- fullnetlist 건 bridge=4 / redundant=96 (원본 이상캡값) → 기생보정 전, 쓰지 말 것.

## 1. 구조 매핑 (확인됨)
- unit = cmom_..._sh, c=4.436fF, weight = `mult`.
- **LSB 5b @ VX**: C0(IN0)=1, C1(IN1)=2, C2(IN2)=4, C3(IN3)=8, C7(IN4)=16
- **MSB 7b @ VOUT**: C6(IN5)=1, C4(IN6)=2, C5(IN7)=4, C8(IN8)=8, C9(IN9)=16, C11(IN10)=32, C10(IN11)=64
- **bridge** C12 (VOUT↔VX)=6, **redundant** C13 (VX↔VSS)=143
- 이상정합비 = Cvx_tot/Y = (31+6+155)/6=32 (155=143+MOM기생~12cu). 보정본이라 sim에서 ~32 나와야 정상.
- ⚠ **INV 인버전**: IN<k> → INV → OUT<k>(바텀플레이트). 즉 plate = ~IN<k>. 선형성(INL/DNL)은 무관, 절대 transfer 부호/오프셋만 반전.

## 2. 시뮬 셋업 (transient, DC 불가 — 캡 open)
- VDD=1, `V (VSS 0) dc=0` 필수.
- **리셋 스위치 2개**(VOUT↔0, VX↔0): analogLib relay, ron 1Ω/roff 1T, vt 0.4/0.6.
- 타이밍: reset [0, 10n] 닫힘 → 10n 열림 → 바텀플레이트 코드스텝 11n → sample 20n (코드창 ≥ 9n).
- 코드 전체 sweep(4096)은 counter/12개 pwl bit소스로 1-tran, 코드창 끝에서 VOUT 샘플.

## 3. 보고 CSV
`cdac_code.csv`: `code, V_VOUT` (전체 4096 또는 carry 코드). 분석은 Claude가:
- INL/DNL (LSB = (Vmax−Vmin)/4095, best-fit line)
- 단조성, MSB carry(2047→2048 등) DNL
- full-scale gain (≈0.905·VDD 예상, calibration이 처리)

## 4. Resume = Monte Carlo (mismatch)
nominal 통과 확인 후 → ADE XL/Assembler, Sampling=LDS, **Mismatch only**, 100~200pt,
PDK 통계 section 필요. 출력: run별 carry코드 VOUT export → σ/3σ(INL/DNL<±0.5LSB?).
