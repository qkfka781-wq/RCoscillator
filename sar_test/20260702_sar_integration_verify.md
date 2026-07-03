# SAR 통합 동작검증 스펙 & 결과

**날짜**: 2026-07-02 | **공정/코너**: Samsung 28FDS, TT / 27°C / presim | **DUT**: `0_BARAM/test_StrongARMfull`

## 1. 대상 정의
- **차동 듀얼채널(ping-pong) 전하재분배 SAR ADC**. 입력 (VRC1−VRC2) → 12b 코드.
- 블록: 비교기 StrongARM ×2(I29/I30), CDAC_12b ×4(I20/22/23/24), TG ×4(샘플), SAR로직 `_sub0`(I6), MUX21 디먹스, (클럭생성 delayline — 이번엔 미사용).
- 채널: ch1=osc1/osc2(CP1/CN1), ch2=osc11/osc22(CP2/CN2). ch1 변환 중 ch2 샘플, 교대.

## 2. 검증 방법 (클럭 직접주입 = 기본구조 TB)
delayline 클럭생성(VCTRL 미완) 우회 — CKR_ASYN을 직접 주입.
- **최소수정**: 넷리스트에서 `I18`(→CKR_ASYN)·`I38`(→ADC_RST) INV 삭제, `V6 CKR_ASYN`·`V7 ADC_RST` = vpwlf/pwl 주입. 비교기클럭·SW·MUX_SEL은 CKR_ASYN/CLK_OSC서 자동생성.
- **PWL** = `sar_test/gen_pwl.py`: CKR_ASYN idle=1, 반주기(2µs)마다 14 active-low 펄스(50MHz), 15슬롯 ADC_RST. ⚠ 시간정밀도 %.12e 필수(안그러면 CMI-2203). ⚠ CKR 폴러리티 idle=1.
- 입력 V3/V4: VRC=500m±200m 차동 10kHz sine (극성 반전으로 양쪽 테스트).
- tran stop=40µs, maxstep 0.5~1n. export: time,osc1/2/11/22,COMP,EOC,MUX_SEL,VRC1/2,CP1<11:0>,CP2<11:0>.
- 분석: 변환채널(MUX_SEL) 코드를 변환창 **+290ns**(리셋 전)에서 읽고 (VRC1−VRC2)와 비교.

## 3. 디버깅 경과 (중요)
1. 100MHz: 이진탐색이 balance 통과 후 overshoot(code 2047). → 초기엔 정착 의심.
2. 50MHz도 동일 → **속도문제 아님**. 내부신호(sar_reusltin.csv) 분석 → **off-by-one 위상버그**: 비트가 자기 트라이얼 평가 전에 캡처(직전 COMP 사용). MSB만 정상(진짜 시퀀서 클럭).
3. **근본원인 = `n<k>` 생성 NAND(I16<k>)의 INV(I17<k>) 라우팅 오류** → phase 어긋남. 수정으로 해결. (nn<k> 지연은 불필요)

## 4. 결과 (수정후, 50MHz, sar_result_fix.csv/fix2.csv)
- **이진탐색 정상 turn-around**: 예 2048→1024→1536→1792→1920(too high,COMP=0)→**1856**→…→1821 안착.
- **모든 변환 balance**: d_osc(osc1−osc2, osc11−osc22) = **0.0000**.
- **양극성 연속 선형 전달함수**:

| 극성 | fit | max resid |
|------|-----|-----------|
| forward (VRC2>VRC1, code 1138~2048) | code = 2279·(VRC1−VRC2) + **2048.0** | 0.7 LSB |
| reverse (VRC1>VRC2, code 2048~2957) | code = 2280·(VRC1−VRC2) + **2046.8** | 0.7 LSB |

→ 같은 기울기·같은 mid(2048)로 **mid-scale 관통 연속 선형**. 1 LSB = 439µV 차동, ±0.7 LSB(near-ideal). 양채널·핑퐁 정상.
- ⚠ k=0 첫 변환만 startup 과도(dvrc≈0서 rail, d_osc 불균형) → 실사용 첫변환 폐기하면 무관.

## 5. 결론
**통합 SAR 기능검증 종결** — 샘플→14사이클 이진탐색→balance→코드가 양채널·양극성 정상. CDAC(±0.06 LSB)·StrongARM(offset~0)의 단독검증과 정합.

## 6. 미해결 / 다음
- 실제 **delayline 클럭 타이밍** 복구(VCTRL/VR_BIAS, project_sar_clock_delayline)시 async 타이밍으로 재검증.
- 100MHz/300MHz 등 고속 재도전(현재 50MHz 검증), PVT/MC.
- DLF 결합(로드맵 4번).
- `_sub0` CP1/CP2 = 조합MUX(래치 아님) 특성 유의.

## 7. 산출물
- `sar_test/netlist`(수정 넷리스트), `sar_test/gen_pwl.py`, `ckr_asyn.pwl`, `adc_rst.pwl`
- 원데이터: `sar_result.csv`(100M), `sar_result50m.csv`(50M overshoot), `sar_reusltin.csv`(내부신호), `sar_result_fix.csv`(수정 forward), `sar_result_fix2.csv`(수정 reverse)
