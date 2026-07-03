# 블록 동작검증 표준 스펙

블록테스트(CDAC→StrongARM→SAR→DLF)마다 아래 3가지를 항상 명시한다.
TB 파일은 사용자가 Virtuoso/ADE에서 직접 구성 — 여긴 "무엇을 넣고 / 어떻게 돌리고 / 무엇을 뽑을지"만.

## 요구 포맷 (블록마다 반복)
1. **Virtuoso schematic 필요 소자** (analogLib / PDK)
   - 전원·바이어스: `vdc`, `vpulse`, `vpwl`, `vsin`, `idc` … 값·핀
   - 자극: 코드/클럭/입력 소스 (pwl·pulse 파형, period/width/rise)
   - 보조소자: 리셋/샘플 스위치 `relay`/`switch` (ron/roff/vt), 캡 `cap`/PDK `cmom·cmim` (floating 노드 셋업·부하)
   - 접지: `V(VSS 0)=0` / `gnd` 필수 여부
2. **시뮬 종류** — `dcOp` / `dc sweep` / `tran`(stop·maxstep) / `parametric sweep`(변수·범위) / `MC`(ADE XL, sampling·pts·section). DC 가능 여부(캡 있으면 tran).
3. **CSV 요구** — 파일명(`*_test/`), 컬럼 정의. 받으면 Claude가 분석(정확도·선형성·마진·σ).

## 공통 규칙
- PDK include·코너(tt/ss/ff, 온도)는 ADE lib에서. presim이면 기생 없음 명시.
- floating 노드(캡 양단)는 반드시 리셋 스위치 또는 .ic.
- self-run(OSC 포함)은 비대칭 .ic 필요. 단일블록은 외부소스로 자극.
- 헤비한 sweep/데이터는 1-tran(counter) 또는 스크립트로, CSV 결과만 전달.

## ⚠ 캡(MOM/MIM) 단일소자 min/max 제약
PDK의 cmom/cmim은 핑거수·면적으로 정해지는 **단일 인스턴스 최소~최대 용량**이 있다.
설계/TB에서 캡 값을 요구할 때 반드시 이 범위 안에서 실현 가능한지 확인:
- 값 > max  → 단일소자 불가 → **병렬(m/mult) 분할** 또는 어레이.
- 값 < min  → **단위캡 fix + weight는 mult로** (CDAC가 이미 이 방식: geometry 고정, mult만).
- CDAC 단위 = cmom 4.436fF(10×10 finger); redundant 143× 등 큰 값은 mult로 실현 → 단일 max 위배 아님.
- OSC = cmim(예 2.276pF/1.12pF), delay 노드 추가캡도 동일 체크.
- **(요청)** 사용자 PDK의 실제 한계값 필요 → 채워지면 아래 표 갱신:

| 종류 | min (단일) | 확장 | 비고 |
|------|-----------|------|------|
| cmom_..._LB_sh | **4.436fF** (10×10 finger, geometry 고정) | "Nb of devices in //"(=mult)로 ×N 병렬 → 위로만 | min 미만 불가. CDAC=이 단위 fix+mult only. lib ST_C32_addon_DP |
| cmim16acc_sh | **63.75fF** (W=L=1.96µm 최소, 더 못 내려감) | **Geometry 모드**: C=16fF/µm²×W·L (연속), 또는 Nb// | 밀도 14.9fF/µm²(실측, 공칭16). lib ST_C32_addon_AMS. min이 cmom의 ~14배 → LSB 불가 |

**cmom 비고**: weight는 Nb// 정수배만 → 단위 4.436fF가 1cu. C13 redundant=143cu, bridge C12=6cu도 Nb//=143/6.
**cmim 비고**: 단위캡 아님(밀도×면적). 목표값→면적 역산. 예 2.276pF→142µm²(12×12), 1.12pF→70µm²(8.4×8.4) @16fF/µm². OSC/decoupling용.

---

## 공통 배치법 (코드자극 + 리셋스위치) — SAR/DLF에도 재사용
- **floating 망 리셋**: `switch`(analogLib, rclosed1/ropen1T/vt 0.4·0.6) 신호핀=노드↔gnd, 제어=RST↔gnd. RST=`vpwl` (0→1, t_rst까지 닫힘, 이후 open). 리셋은 처음 1회(선형 charge-redist라 코드램프 중 재리셋 불필요).
- **N비트 코드 전체 sweep = 이진카운터 트릭**: 비트 k를 `vpulse`로 `delay=t_rst+2^k·Tcode, width=2^k·Tcode, period=2^(k+1)·Tcode` → 한 tran에 0→(2^N−1) 카운터. 총 = 2^N·Tcode.
- **INV 경유 시**: vpulse v1/v2 반전(1/0)으로 구동해 plate=정코드. 안 하면 plate=보수 → 해석때 보정.
- 출력은 `time, V_node` 전체 export → Claude가 코드창 끝에서 슬라이스.

## 1. CDAC_12b  (→ 상세 cdac_test/README.md, schematic_setup.md)
- **소자**: VDD `vdc`=1, `V(VSS 0)`=0; 리셋 relay ×2 (VOUT↔0, VX↔0, ron1Ω/roff1T, vt0.4/0.6);
  코드자극 = IN<11:0> 12개 `vpwl`/counter (plate=~IN, INV경유); 캡=PDK cmom(셀 내장).
- **시뮬**: `tran` stop=20n·코드창≥9n (DC불가). 전체4096=counter 1-tran. → resume: `MC`(ADE XL, LDS, mismatch only, 100~200pt).
- **CSV**: `cdac_test/cdac_code.csv` = `code, V_VOUT`.
- ⚠ netlistafter 버전(bridge6/redundant143) 사용. fullnetlist(4/96)는 보정전.

## 2. StrongARM = SAR 비교기  (✔ 1차 완료 2026-07-01 → 상세 strongarm_test/20260701_sar_comparator_verify.md)
- **용도**: SAR 비교기(VINP/VINN = CDAC/TG output). CLK high=eval. nMOS 입력쌍 lvtnfet W160/L80.
- **방식**: `strongarm_test/build_strongarm_tb.il` — 클럭비교기 + 차동삼각파(V_DIFF ±5m) + CM삼각파(V_CM 0.2↔0.8) 1-tran. export `time,VINP,VINN,CLK,OUT`.
- **결과**(TT/27/300MHz): 정상영역 offset~0·감도<40µV·클린. but **CM<~0.33V 오판(≤0.25V 50%, 0.35V 0%)** = nMOS 저CM 한계. SAR CM 하한 0.2V가 실패영역.
- ⭐ **미해결**: 실제 비교시점 CM이 0.2까지 스윙하는지 확인 → 유지면 합격, 하강이면 fix(①CM≥0.4 유지 ②double-tail/pMOS입력).
- ⚠ OSC용 refn 300m StrongARM은 별건.

## 3. SAR 동작  (✔ 완료 2026-07-02 → 상세 sar_test/20260702_sar_integration_verify.md)
- test_StrongARMfull(차동 듀얼채널 SAR). 클럭 직접주입 TB(delayline 우회, CKR_ASYN vpwlf 14펄스/반주기).
- **근본버그=`n<k>` NAND의 INV 라우팅 오류(phase off-by-one)** → 수정 완료. (nn<k> 지연 불필요)
- **결과**(50MHz): 이진탐색 turn-around 정상, 모든 변환 d_osc=0 balance, **양극성 연속선형 code=2279·(VRC1−VRC2)+2048, ±0.7 LSB, 1LSB=439µV**. 양채널·핑퐁 정상. k=0 startup만 예외.
- 남음: delayline 실타이밍 복구시 재검증, 고속(100/300M)·PVT/MC.

## 4. DLF 동작  (✔ 완료 2026-07-02 → 상세 dlf_test/20260702_dlf_verify.md)
- DLF=`_sub3`(17b 누적기, netlist=RCnetlist 풀칩 내). DIFF=DREF−(DD2−DD1) → α배럴시프트(ALPHA1<1:0>, 00=×32…11=×1) → acc+=α·DIFF → ±acc(CLK_OSC)→D<16:0>→CDAC_17b→oref.
- **결과**: acc 누산·oref 변환 정상. ⚠ startup(리셋후 DD2 먼저·DD1=0 → DIFF≈−2000 → α×32로 ACC overflow) → **α 작게로 우회**. 근본해결=첫 누산 마스킹.
- 다음: 전체 폐루프(4c) — RC osc+SAR+DLF+oref feedback (startup 마스킹 필요 가능).
