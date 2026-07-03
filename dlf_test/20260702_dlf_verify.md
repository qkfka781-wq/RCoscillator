# DLF 단독검증 스펙 & 결과

**날짜**: 2026-07-02 | **공정/코너**: Samsung 28FDS, TT / 27°C / presim | **DUT**: `0_BARAM/_sub3` (+ CDAC_17b oref) | 넷리스트: `RCoscillator/RCnetlist` (풀칩 0_TOP_RC 내)

## 1. 대상 정의
- **DLF = 17비트 단순 누적기**(디지털 루프필터). 두 페이즈 SAR 코드차를 적분해 oref 조절.
- 설계식(노트 project/20260330_dlf.md): `DIFF=DREF−(DD2−DD1)`, `acc[n+1]=acc[n]+α·DIFF`, `Voref=0.5−(acc−65536)·1µV`.

## 2. 구조 (_sub3, 트레이스 확정)
| 단계 | 블록 | 동작 |
|------|------|------|
| ① CP 캡처 | I0 DFFQ×12 (clk=DATA_OUT) | CP<11:0>→DD0 |
| ② 페이즈 분리 | I3 DFFRPQ(CLK_DATA↑)/I6(~CLK_DATA↑) | DD0→DD1_SAMPLE / DD2_SAMPLE |
| ③ 코드차 | I12 ADDER_12b | DIFF_SAMPLE=DD2−DD1 |
| ④ 에러 | I14 INV+I13 ADDER_12b | DIFF=DREF−(DD2−DD1) |
| ⑤ α scale | I15 MUX41×17 (sel=ALPHA1<1:0>) | DIFF 부호확장 shift. **00=×32(shift5,최대) … 11=×1(shift0,최소)** |
| ⑥ 누산 | I16 ADDER_17b + I18/I17 DFFSQ(clk=CLK_DATA, preset=EN11) | SUM=ACC+α·DIFF, ACC←SUM. EN11→ACC 초기 mid(65536) |
| ⑦ ±acc | I19~21/I24 INV + I22 MUX21(sel=~CLK_OSC) | CLK_OSC=0→D=ACC / =1→D=~ACC → D<16:0>→CDAC_17b→oref |

## 3. 검증 (goal A: 임의 CP → acc → oref)
- `_sub3`+`CDAC_17b` 인스턴스, CP<11:0>·DATA_OUT·CLK_DATASAMPLE·CLK_OSC·EN/EN11 자극, D<16:0>·oref 관찰.
- ALPHA1=00→차차 축소, DREF_IN=0.

## 4. 결과
- ✅ **acc 누산 정상, oref 변환 동작 확인** (carry-over 없을 때).
- ⚠ **startup 아티팩트**: 리셋 후 DD1=0인데 **DD2가 먼저** 유효값(~2000)이 되면 `DIFF=DREF−(DD2−DD1)=−(2000−0)≈−2000` → α=00(×32)으로 ≈−64000 → **ACC 17b overflow(carry-over)**.
  - **우회**: α 작게(ALPHA 코드↑=이득↓) → DIFF 안 뻥튀기 → 정상 누산 ✓ ("일단").
  - 정상상태에선 DD1/DD2 둘 다 실값 → DIFF 작음 → 무관.

## 5. 결론 & 다음
- **DLF 단독 기능검증 통과** (acc+oref). startup은 α로 우회.
- **근본해결(폐루프 권장)**: 첫 누산 마스킹(DD1·DD2 둘 다 유효 전 누산금지) / DD1 유효초기화 / 첫 DIFF 클램프.
- **다음 = 전체 폐루프(4c)**: RCnetlist(0_TOP_RC) RC osc+SAR+DLF+oref feedback, tran 80µs. startup 마스킹 필요 가능. α로 loop 안정성/수렴속도 튜닝.

## 6. 산출물
- 넷리스트: `RCoscillator/RCnetlist` (풀칩, _sub3 DLF + CDAC_17b 포함)
- 설계노트: `circuit/project/20260330_dlf.md`
