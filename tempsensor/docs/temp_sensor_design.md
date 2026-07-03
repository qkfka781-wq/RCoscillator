# RC Oscillator 내장 온도 센서 설계

## 1. 무엇을 하는가

RC Distributed Oscillator 내부에 **별도의 RC network**를 추가하고, 기존 SAR ADC의 idle 구간을 활용하여 온도를 측정한다.

---

## 2. 동작 원리

> 이미지: `img/04_temp_principle.svg`

RC network에 전압을 걸면, 노드 전압이 **RC 시정수(τ = R × C)에 따라** 충전된다.

R(opppcres)은 온도에 따라 저항값이 변하므로, **같은 시간 동안 충전했을 때 도달하는 전압이 온도마다 다르다.** 이 전압을 ADC로 읽으면 온도 정보를 얻을 수 있다.

---

## 3. 전체 동작 흐름

> 이미지: `img/01_block_diagram.svg`

매 CLK_OSC half-cycle마다 아래 시퀀스가 반복된다:

**1단계: 충전**
- RC network에 VDD를 인가하여 충전 시작
- TG(Transmission Gate) ON → ADC 입력(temps)이 RC 전압(VRC_temp)을 추종

**2단계: 전압 hold + ADC 변환**
- Delay line D[30] 도달 → temp_en 신호 발생
- TG OFF → temps 전압이 **그 순간의 값으로 고정**
- Temp SAR ADC가 고정된 전압을 12-bit으로 변환

**3단계: 리셋**
- ADC 변환 완료 → temp_data_out pulse 발생
- RC network 3노드를 **동시에 0V로 초기화**
- 다음 phase에서 동일한 과정 반복

---

## 4. 타이밍

> 이미지: `img/02_timing_diagram.svg`

| 순서 | 구간 | VRC_temp | temps (ADC 입력) | TG |
|------|------|----------|------------------|----|
| 1 | 충전 + Cal SAR | 0V → 상승 | VRC_temp 추종 | ON |
| 2 | Temp ADC 변환 | (계속 상승) | **고정 (hold)** | OFF |
| 3 | 리셋 | → 0V | → 0V | ON |
| 4 | 대기 | 0V 유지 | 0V 유지 | ON |

---

## 5. 시뮬레이션 결과

> 이미지: `img/05_adc_result.svg`

| 온도 | Phase A | Phase B |
|------|---------|---------|
| -30°C | 3583 | 3456 |
| 9°C | 3583 | 3472 |
| 30°C | 3736 | 3682 |
| 60°C | 3789 | 3767 |
| 90°C | 3851 | 3843 |
| 120°C | 3927 | 3925 |

- 12-bit ADC, 감도 ~2.7 LSB/°C, 단조 증가
