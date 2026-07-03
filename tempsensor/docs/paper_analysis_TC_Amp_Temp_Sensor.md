# 논문 분석: TC Amplifier 기반 온도 센서

**"A Temperature Coefficient Amplifier based Temperature Sensor With 41fJ·K² Resolution FoM"**
Kangmin Jeong et al., JSSC (Sim 교수님 그룹, POSTECH)

---

## 1. 풀려는 문제

기존 온도 센서의 공통 한계: **온도 신호(gradient)는 작고(1~2mV/°C), DC offset은 크다(수백mV).**

| 방식 | 감도 | 문제 |
|------|------|------|
| BJT (ΔVBE) | 0.1~0.2 mV/°C | 전력 μW급, 비선형 → polynomial fitting 필요 |
| MOSFET (subthreshold) | 작음 | 비선형 (log 필요), process variation 큼 |
| Resistor | TC 있으나 2차항 | 비선형, 2-point calibration 필요 |

ADC dynamic range 대부분이 offset에 낭비됨 → 직접 증폭하면 rail에 포화.

---

## 2. 핵심 아이디어: TC Amplifier

**DC offset은 줄이고, 온도 gradient만 선택적으로 증폭.**

기존 CTAT, PTAT 신호:
```
VCTAT(T) = -α·(T-T0) + o1    (offset o1 크고, gradient α 작음)
VPTAT(T) = +β·(T-T0) + o2    (offset o2 크고, gradient β 작음)
```

둘을 빼면:
```
VCTAT - VPTAT = -(α+β)·(T-T0) + (o1-o2)
                 ↑ gradient 합산     ↑ offset 상쇄
```

N-stage stacking → gradient **N배** 증폭, offset은 supply rail 내에서 관리.

---

## 3. TC Amplifier 회로

M1 (common-source) + M2 (diode-connected load), 둘 다 subthreshold 동작.

Gate에 VCTAT 인가 시 출력:
```
Vx = VCTAT + mn·VT·ln(W1/L1 / W2/L2)
                      ↑ negative PTAT (W2/L2 > W1/L1일 때)
```

- **Vth 상쇄**: 같은 device type, 같은 body bias → process variation에 강함
- NMOS stack: VDD 기준, 온도↑ → 전압↓
- PMOS stack: GND 기준, 온도↑ → 전압↑
- 차동 구성 → TC 추가 2배

---

## 4. 전체 시스템 구성

```
BGR (0.38nW)
  │ VCTAT (~1mV/°C)
  ▼
TC Amplifier (2.63nW)
  ├── VNOUT (NMOS 5-stack, VDD 기준, 온도↑→↓)
  └── VPOUT (PMOS 5-stack, GND 기준, 온도↑→↑)
        │ 차동: ~10mV/°C 이상 (gradient 증폭됨)
        ▼
13-bit Split-CDAC SAR ADC (16.3nW)
  │
  ▼
Digital Code (온도 선형 대응, polynomial fitting 불필요)

+ LDO ×2 (각 ~0.75nW): VDDAMP, VREFADC 안정화
```

---

## 5. 세부 블록

### BGR (Bandgap Reference)
- Hybrid BJT-MOS 구조
- VBE - Vth 기준 전압 생성
- Fringing field 효과로 Vth process 보상
- 0.38nW

### LDO ×2
- Subthreshold 차동 amplifier 기반
- TC Amp용 VDDAMP + ADC용 VREFADC
- 각 ~0.75nW, DC gain 53.6dB @27°C

### SAR ADC
- 13-bit split-CDAC (7-bit MSB + 6-bit LSB)
- MIM cap 20.28fF (180nm 최소 unit)
- Bridge cap (Y·C) + redundant cap (X·C)로 parasitic 보상
- Thick oxide MOSFET으로 leakage 억제
- 16.3nW (전체 전력의 78%)

---

## 6. 측정 결과

| 항목 | 값 |
|------|-----|
| 공정 | 180nm CMOS |
| 전력 | **20.8nW** |
| 온도 범위 | -20°C ~ 100°C |
| Resolution | **22.2mK** |
| Inaccuracy (1pt trim) | **±1.44°C (3σ)** |
| Inaccuracy (untrimmed) | ±3°C (3σ) |
| Resolution FoM | **41 fJ·K²** (MOS 기반 최고) |
| Conversion time | 4ms |
| Conversion energy | 83pJ |
| Area | 0.34 mm² |
| Supply | 1.8V (min) |
| Line sensitivity | 0.27°C/V |

### 전력 분배
| 블록 | 전력 | 비율 |
|------|------|------|
| SAR ADC | 16.3nW | 78% |
| TC Amplifier | 2.63nW | 13% |
| LDO ×2 | 1.48nW | 7% |
| BGR | 0.38nW | 2% |
| **합계** | **20.8nW** | 100% |

---

## 7. 논문의 핵심 contribution

1. **TC Amplification**: offset 억제 + gradient 선택 증폭 → ADC 요구 사양 완화
2. **Intrinsic linearity**: TC Amp 출력이 온도에 선형 → digital backend polynomial fitting 불필요
3. **All-subthreshold**: 전체 아날로그 20.8nW → IoT/SoC sleep mode 적합
4. **1-point trim 충분**: Vth 상쇄 구조로 process variation에 강함
5. **41 fJ·K² FoM**: MOS 기반 센서 중 최고 기록

---

## 8. 한계 / Trade-off

| 항목 | 내용 |
|------|------|
| Area | 0.34mm² (BJT + TC Amp + LDO + ADC 모두 포함) |
| Supply | 최소 1.8V (TC Amp 5-stage stacking headroom 필요) |
| 속도 | 4ms/conversion (IoT 충분, 실시간 모니터링엔 느림) |
| 공정 | 180nm (최신 공정 대비 큰 면적, 하지만 BJT 성능 유리) |
| 1V 동작 | N=5 불가, N=2~3 가능할 수 있으나 성능 저하 |

---

## 9. State-of-the-Art 비교 (Table I 기준)

| | 이 논문 | ISSCC'25 | VLSI'25 | JSSC'25 | ISSCC'18 |
|---|---|---|---|---|---|
| Type | PNP+MOS | NPN | Metal R | PNP | PNP+MOS |
| Tech | 180nm | 180nm | 1.8nm GAA | 4nm | 22nm |
| Power | **20.8nW** | 3.36μW | 86.4μW | 3.4μW | 35μW |
| Inaccuracy | ±1.44°C | ±0.15°C | ±1.4°C | ±0.22°C | ±0.5°C |
| Resolution | 22.2mK | 0.38mK | 14.6mK | 0.58mK | 7.8mK |
| FoM (fJ·K²) | **41** | 64 | 1550 | 78 | 246 |
| Calibration | 1-point | 1-point | 1-point | 1-point | 1-point |
| Area | 0.34mm² | 0.05mm² | 0.00092mm² | 0.0061mm² | 0.0043mm² |
