# CDAC_12b 검증 스키매틱 배치법 (ADE에서 직접)

목표: CDAC_12b 인스턴스 하나 + 코드자극 + 리셋스위치 → transient로 전체 transfer.
TB는 본인이 Virtuoso에서 구성. 아래는 "무엇을 어디에 어떤 값으로".

## 0. 배치 개요
```
   VDD(vdc=1)
     │
  ┌──┴───────────────────────────┐
  │        CDAC_12b (DUT)         │
  │  IN<11:0>  VOUT  VX  VDD VSS  │
  └───┬─────────┬────┬──────┬─────┘
   IN소스12개  SW_o  SW_x   gnd
   (vpulse)    │     │
            gnd(0) gnd(0)
   SW 제어 ← RST(vpwl)
```
- VOUT, VX 둘 다 floating top plate → **각각 리셋 스위치로 0V 초기화** 필수.
- IN<k> → (셀 내부 INV) → OUT<k> = bottom plate. **plate = ~IN<k>**.

## 1. 전원·접지 (analogLib) — 그라운드 네트명 = VSS 통일
- `vdc` : VDD ↔ VSS, dc=1
- VSS = 0 기준: VSS 네트에 `gnd` 심볼 1개 또는 `V(VSS 0)=0`. (모든 소스 return도 VSS 라벨)

## 2. 리셋 스위치 ×2 (analogLib `switch`)
신호핀 2 + 제어핀 2. 제어 > vt2면 닫힘(rclosed).
| 인스턴스 | 신호핀 | 제어핀 | 파라미터 |
|---|---|---|---|
| SW_o | VOUT ↔ VSS | RST ↔ VSS | rclosed=1, ropen=1T, vt1=0.4, vt2=0.6 |
| SW_x | VX ↔ VSS | RST ↔ VSS | 동일 |

- **RST 소스** = `vpwl`: `(0 1) (t_rst 1) (t_rst+10p 0)` → [0,t_rst] 닫힘(=0V로 리셋), 이후 영구 open.
- t_rst = 10n.
- ⭐ **리셋은 처음 1번만**. 망 charge가 Q=0으로 고정된 뒤 코드를 램프해도, 선형 charge-redistribution이라 매 코드마다 올바른 VOUT 나옴(재리셋 불필요).

## 3. 코드 입력 IN<11:0> — 이진카운터 트릭 (전체 4096 한 tran)
12개 `vpulse`로 0→4095 카운터 생성. bit_k는 period 절반마다 토글.
- **Tcode = 10n** (코드창), 총 램프 = 4096×10n = **40.96µs**.
- **INV 보정**: vpulse를 **v1=1(rest VDD), v2=0(pulse 0)** 으로 반전 구동 → INV 거치면 bottom plate가 up-counter(증가코드) 따라감. (v1=0/v2=1로 놓으면 plate=보수코드 → 해석때 code=4095−n 보정 필요)
- 공통: rise=fall=10p.

| IN | delay | width(pw) | period |
|---|---|---|---|
| IN0 | 20n | 10n | 20n |
| IN1 | 30n | 20n | 40n |
| IN2 | 50n | 40n | 80n |
| IN3 | 90n | 80n | 160n |
| IN4 | 170n | 160n | 320n |
| IN5 | 330n | 320n | 640n |
| IN6 | 650n | 640n | 1.28u |
| IN7 | 1.29u | 1.28u | 2.56u |
| IN8 | 2.57u | 2.56u | 5.12u |
| IN9 | 5.13u | 5.12u | 10.24u |
| IN10 | 10.25u | 10.24u | 20.48u |
| IN11 | 20.49u | 20.48u | 40.96u |

규칙: `delay_k = t_rst + 2^k·Tcode`, `width_k = 2^k·Tcode`, `period_k = 2^(k+1)·Tcode`.

## 4. 시뮬 / 출력
- **tran**: stop = t_rst + 40.96µs ≈ **41µs**, maxstep ≤ 1n (선형망이라 빠름).
- 저장: VOUT (옵션 VX). export `cdac_test/cdac_code.csv` = `time, V_VOUT`.
  → Claude가 각 코드창 끝(t_rst + n·Tcode + 0.9·Tcode)에서 슬라이스해 (code,VOUT)→INL/DNL 계산.
- 빠르게 줄이려면 Tcode=5n (총 ~20µs)도 OK.

## 5. 사전 확인
- C13(redundant) Nb//=143, C12(bridge) Nb//=6.
- VDD=1, VSS=gnd, presim(기생없음)인지 코너 명시.
