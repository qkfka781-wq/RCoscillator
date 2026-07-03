# 0_RC_Oscillator Netlist Analysis

## 1. Top-Level Hierarchy

```
0_RC_Oscillator (top)
  |
  +-- _sub0 (1_RCOSC)          : RC Oscillation Core
  |     +-- RCDIFF_COMP x2     : Differential comparators
  |     +-- TG x4              : Transmission gate (sampling)
  |     +-- CDAC_17b           : 17-bit CDAC (oref generation)
  |     +-- CDAC_test x4       : 12-bit CDAC (SAR sampling)
  |     +-- COMPARATOR2 x2     : Strong-ARM latch comparator
  |     +-- Distributed RC     : R + C passive network
  |     +-- SR Latch logic     : CLK_OSC generation
  |
  +-- _sub1 (1_SAR_alpha)      : SAR ADC + Digital Calibration Loop
  |     +-- SAR_LOGIC_12bit    : 12-bit SAR shift-register logic
  |     +-- ADDER_12bit x3     : Subtractor/adder (DD2-DD1, DD1+DD2, DREF-DIFF)
  |     +-- ADDER_17bit        : 17-bit accumulator adder (ACC + alpha*DIFF)
  |     +-- MXT4 x17           : 4:1 MUX barrel shifter (alpha scaling)
  |     +-- DFF banks          : DD0, DD1_SAMPLE, DD2_SAMPLE, ACC registers
  |
  +-- _sub2 (1_SAR_CLOCK)      : Clock Generation
  |     +-- DELAY_LINE2 x30    : Current-starved delay chain
  |     +-- XNOR2 x15          : Settling detector
  |     +-- NAND/OR tree       : All-settled → CKR_ASYN (async SAR clock)
  |
  +-- TG (I15)                 : oref initialization (Vmid → oref at startup)
  +-- Voltage sources          : VDD, VSS, refn, Vmid, DREF, EN
```

---

## 2. Design Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| PDK | Samsung 28nm (LNR28LPP) | section=nn |
| VDD | 1.0 V | |
| VSS | 0 V | |
| refn | 0.5 V | Comparator tail bias reference |
| oref (initial) | 0.5 V | IC statement |
| DREF<11:0> | all 0 | Target differential code = 0 |
| ALPHA1<1:0> | external | Loop gain select (x1/x0.5/x0.25/x0.125) |
| Simulation | tran 80us | conservative error preset |

---

## 3. Oscillation Core (_sub0) 상세 분석

### 3-1. Distributed RC Network

3-stage distributed RC, Koo 2023 최적 스케일링(Rn=2Rn-1, Cn=Cn-1/2) 적용:

```
         R1=200.5k      R2=401k        R3=802k
CLK_Q ----[R0]---- d1 ----[R4]---- dd1 ----[R5]---- VRC1
                    |                |
                   C6(2C)          C7(C)
                    |                |
                  CLK_QB           CLK_QB

         R1=200.5k      R2=401k        R3=802k
CLK_QB ---[R6]---- n0147 --[R7]---- n0148 ---[R8]---- VRC2
                    |                |
                   C2(2C)          C3(C)
                    |                |
                  CLK_Q            CLK_Q
```

**Resistor (opppcres):**
| Name | Value | Segments | Role |
|------|-------|----------|------|
| R0, R6 | 200.491 kOhm | s=81 | R1 (1st stage) |
| R4, R7 | 400.982 kOhm | s=162 | R2 = 2*R1 (2nd stage) |
| R5, R8 | 801.965 kOhm | s=324 | R3 = 4*R1 (3rd stage) |

**Capacitor (vncap, cross-coupled to complementary phase):**
| Name | W x L | Node | Role |
|------|-------|------|------|
| C6, C2 | 20.13u x 74u | d1/n0147 → CLK_QB/CLK_Q | 2C (larger, 1st node) |
| C7, C3 | 20.13u x 37u | dd1/n0148 → CLK_QB/CLK_Q | C (smaller, 2nd node) |

**Cross-coupling 핵심:** Capacitor가 **반대 phase(CLK_QB/CLK_Q)**에 연결됨 → BPF 특성 생성, comparator crossing 시점에서 slope boosting 효과.

**oref decoupling:** C4 = vncap 50.09u x 30u (oref to VSS)

### 3-2. Comparator 구조

**RCDIFF_COMP** (I53, I7): Enable 가능한 differential current-mode comparator
- Port 순서: (ON OUT VDD VINN VINP VREFN VSS)
- I53: ON=SW1, VINP=VRC1, VINN=oref → **VRC1 > oref** 판별 (Phase A 활성)
- I7: ON=SW2, VINP=oref, VINN=VRC1 → **oref > VRC1** 판별 (Phase B 활성)

내부 구조:
- Input pair: N1(VINP), N0(VINN) → W=0.72u, L=30nm, nf=6 (large gm)
- Tail current: N3(ON) → enable gate, N4/N5(VREFN) → bias (W=0.32u, L=83nm)
- Active load: P0/P1(cross-coupled), P2/P3(current mirror) → W=0.32u, L=83nm
- Output stage: N7/N2(diode+mirror) → digital-level output

**COMPARATOR2** (I92, I95): Strong-ARM latch comparator
- Port: (CLK OUT OUTB VDD VINN VINP VSS)
- I92: CLK=CLK_ASYN1, compares osc2 vs osc1 (Phase A sampled differential)
- I95: CLK=CLK_ASYN2, compares osc22 vs osc11 (Phase B sampled differential)
- 출력: NOR-based SR latch → OUT/OUTB

### 3-3. Transmission Gate Sampling

| Instance | Control | Input | Output | Active Phase |
|----------|---------|-------|--------|-------------|
| I138 | SW1/SW2 | VRC1 | osc1 | Phase A (SW1=H) |
| I137 | SW1/SW2 | VRC2 | osc2 | Phase A (SW1=H) |
| I88 | SW2/SW1 | VRC1 | osc11 | Phase B (SW2=H) |
| I90 | SW2/SW1 | VRC2 | osc22 | Phase B (SW2=H) |

TG size: W=3u, nf=15 (large, low Ron for accurate sampling)

### 3-4. CLK_OSC Generation Logic

```
RCDIFF_COMP output → outp/outn
  ↓
MX2 (I46, I145): CMP selects between outp/outn routing
  ↓
NOR3 + NOR2: SR latch with enable (EN, ENB)
  ↓
NAND2 (EN gating) → OUT_PULSE
  ↓
INV chain → CLK_OSCB → CLK_OSC
```

- outp 리셋: N6 (SW2로 pull-down, W=40nm)
- outn 리셋: N0 (SW1로 pull-down, W=40nm)

### 3-5. CLK_Q / CLK_QB 생성

CLK_OSC → 3-stage BUF chain → CLK_Q
CLK_OSCB → 3-stage BUF chain → CLK_QB

이 클럭이 RC network의 충방전을 제어.

### 3-6. CDAC_17b (oref 생성)

17-bit binary weighted capacitive DAC:
- MSB section (C24~C29): VOUT node, 288f ~ 4.5f
- LSB section (C22, C33~C30): VX node, 4.1f ~ 65.6f
- Bridge cap (C34): VX-VM = 16.6f, VM-VOUT = C20 = 16f
- Reference caps: C19(VM-VSS)=314.4f, C21(VX-VSS)=387.5f
- Input: D<16:0> via INV → binary switching
- CAL inputs: all tied to VSS (unused)

### 3-7. oref Initialization

- P6/N8: DMID controlled switch → oref을 VDD/2로 초기화
  - P6: W=0.44u, nf=10 (PMOS pull-up)
  - N8: W=0.4u, nf=10 (NMOS pull-down)
- Top-level I15: TG(ENB/EN controlled) → Vmid(0.5V) → oref (EN 활성 전 초기화)

---

## 4. SAR ADC + Digital Calibration Loop (_sub1) 상세 분석

### 4-1. SAR ADC (SAR_LOGIC_12bit)

- 12-bit shift-register based SAR logic
- Clock: CKR_ASYN (asynchronous, settling-based)
- DFF chain: CLK<12> → CLK<0> → DATA_OUT → EOC
- CP<11:0>: SAR comparison result → CN<11:0> = ~CP (complementary)
- DFFSRPQ: bit decision registers with set/reset

### 4-2. Data Sampling & Phase Separation

```
SAR output CP<11:0> → DFF(DD0) on DATA_OUT
  ↓
DD0 → DFF(DD1_SAMPLE) on CLK_DATA rising  → Phase A code
DD0 → DFF(DD2_SAMPLE) on CLK_DATA falling → Phase B code
```

MUX_SEL (= buffered CLK_OSC) routes:
- Phase A (MUX_SEL=L): COMP=COMP1, CP1=CP, CN1=CN → CDAC_test I91/I93
- Phase B (MUX_SEL=H): COMP=COMP2, CP2=CP, CN2=CN → CDAC_test I0/I1

### 4-3. Digital Loop 연산

```
Step 1: DIFF_SAMPLE = DD2 + (~DD1) + 1  (= DD2 - DD1, 2's complement)
        → ADDER_12bit I24

Step 2: DIFF = DREF + (~DIFF_SAMPLE) + 1 (= DREF - DIFF_SAMPLE)
        → ADDER_12bit I26

Step 3: DIFF_OUT1 = alpha * DIFF  (barrel shift via MXT4)
        → ALPHA1<1:0> = {00: x1, 01: x0.5, 10: x0.25, 11: x0.125}
        → Sign extension 포함 (17-bit output)

Step 4: SUM = ACC + DIFF_OUT1  (17-bit accumulation)
        → ADDER_17bit I13

Step 5: ACC[n+1] = SUM (registered on CLK_OSC rising)
        → DFFRPQ I144<15:0>, DFFSQ I147 (MSB)

Step 6: D<16:0> = ACC or ~ACC (MX2, CLK_OSC phase dependent)
        → CDAC_17b → oref
```

**Loop equation:**
```
DIFF[n] = DREF - (DD2 - DD1)[n]
ACC[n+1] = ACC[n] + alpha * DIFF[n]
oref = CDAC(ACC)
```

### 4-4. SUM/DMID Detection

ADDER_12bit I12: DD1 + DD2 → SUM_SAMPLE (carry = DDMID1)
DFFSQN I169: DMID1 = ~DDMID1 (sampled on CLK_DATA)
→ oref 초기화 제어에 사용

---

## 5. Clock Generation (_sub2) 상세 분석

### 5-1. Delay Line

30-stage DELAY_LINE2 chain:
- CLK_OSC → DELAY_LINE2[0] → ... → DELAY_LINE2[29]
- Each stage: current-starved inverter pair
  - Bias: self-biased current mirror (R=200.5k → P5 mirror → N tail)
  - 2-stage inversion with current limiting

### 5-2. Asynchronous SAR Clock (CKR_ASYN)

```
CLK_D<0:29> (buffered delay outputs)
  ↓
XNOR2 pairs: CLK_D[2k] XNOR CLK_D[2k+1] → settled?
  ↓
NAND4 + NAND3 + OR4 tree: all 15 pairs settled?
  ↓
INV → CKR_ASYN (SAR conversion clock)
```

RC network이 settle되면 모든 delay output이 동일 → XNOR=1 → CKR_ASYN 활성

### 5-3. Clock Routing

| Signal | Source | Description |
|--------|--------|-------------|
| SW1 | BUF(CLK_OSC) | Phase A switch control |
| SW2 | BUF(CLK_OSCB) | Phase B switch control |
| MUX_SEL | 3-stage BUF(CLK_OSC) | SAR MUX phase select |
| CLK_CMP | INV(CLK_D<14>) | Comparator trigger (mid-delay) |
| CLK_DATASAMPLE | BUF(CLK_D<28>) | Data sampling clock |
| RC_CLK | BUF(CLK_D<29>) | Final delayed clock output |
| ADC_RST | INV(CLK1_ASYN<14>) | ADC reset |
| CLK_ASYN1 | NAND(settled, SW2) | Phase A comparator clock |
| CLK_ASYN2 | NAND(settled, SW1) | Phase B comparator clock |

---

## 6. Standard Cell Library

A9TR track, Samsung 28nm:

| Cell | Function |
|------|----------|
| INV_X0P5B_A9TR | Inverter |
| BUF_X0P7B_A9TR / BUF_X0P7M_A9TR | Buffer |
| NAND2_X0P5B_A9TR | 2-input NAND |
| NOR2_X0P5B_A9TR | 2-input NOR |
| NOR3_X0P5M_A9TR | 3-input NOR |
| NAND3_X0P5A_A9TR | 3-input NAND |
| NAND4_X0P5A_A9TR | 4-input NAND |
| NAND2B_X0P5M_A9TR | NAND2 (1 inverted input) |
| OR4_X0P5M_A9TR | 4-input OR |
| XNOR2_X0P5M_A9TR | 2-input XNOR |
| MX2_X0P5B_A9TR | 2:1 MUX |
| MXT4_X0P5M_A9TR | 4:1 MUX |
| DFFQ_X0P5M_A9TR | DFF (Q only) |
| DFFRPQ_X0P5M_A9TR | DFF with async reset |
| DFFSQ_X0P5M_A9TR | DFF with async set |
| DFFSQN_X0P5M_A9TR | DFF with async set (QN) |
| DFFSRPQ_X1M_A9TR | DFF with set + reset |
| ADDF_X1M_A9TR | Full adder |

---

## 7. Passive Devices

| Type | Model | Parameters |
|------|-------|------------|
| Resistor | opppcres | P+ poly, w=0.15u, various lengths |
| Capacitor (RC network) | vncap | Vertical natural cap, botlev=15, toplev=19 |
| Capacitor (CDAC) | capacitor | Ideal caps, binary weighted |

---

## 8. Signal Flow Summary

```
              Distributed RC Network
                (slope boosting)
                      |
CLK_Q/CLK_QB ←→ R1-R2-R3 + C(cross) → VRC1/VRC2
                      |
                      ↓
              RCDIFF_COMP x2
           (VRC1 vs oref comparison)
                      |
                      ↓
              SR Latch → CLK_OSC
                      |
          +-----------+-----------+
          |                       |
    TG Sampling              30-stage Delay
   (osc1/2, osc11/22)        (CLK_D chain)
          |                       |
    COMPARATOR2 x2          Settling Detect
   (differential SAR)       (XNOR + logic)
          |                       |
    SAR_LOGIC_12bit          CKR_ASYN
   (CP/CN output)           (SAR clock)
          |                       |
    DFF: DD0 → DD1/DD2 sampling
          |
    DIFF = DREF - (DD2 - DD1)
          |
    alpha scaling (MXT4 barrel shift)
          |
    ACC[n+1] = ACC[n] + alpha*DIFF
          |
    CDAC_17b → oref → comparator reference
```
