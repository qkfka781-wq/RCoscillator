---
name: Koo, Sim & Theogarajan 2026 - Parasitic/Mismatch Tolerant Fully Common-Centroided Split-CDAC
description: 12b split-CDAC (7b MSB + 5b LSB). 단위 커패시터 기반 bridge cap (Y=6C)으로 기생 민감도 6배 개선, 면적 효율 12배. MOM cap, 65nm, INL < 1.2LSB (21칩, 보정 없음).
type: reference
---

# Koo, Sim & Theogarajan, IEEE TVLSI 2026
**"A Parasitic and Mismatch Tolerant Fully Common-Centroided and Shielded Split-CDAC With Identical Unit Capacitors for SAR-ADC"**
- 저널: IEEE Transactions on VLSI Systems, Vol.34, No.1, Jan. 2026
- 저자: Jahyun Koo (세종대), Jae-Yoon Sim (POSTECH), Luke Theogarajan (UCSB)
- 공정: **65nm CMOS** | Supply: 3.3V/0.6V | Fs: 100kS/s | 면적: 0.013mm²

---

## 구조 개요

### Split-CDAC 구성 (12b = 7b MSB + 5b LSB)

| 파라미터 | 값 | 설명 |
|----------|----|------|
| 총 해상도 | **12b** | m=7 (MSB), n=5 (LSB) |
| Bridge cap (Y) | **6C** | 단위 커패시터 6개 → 기생 민감도 6배 개선 |
| Redundant cap (X) | **155C** | X = (Y-1)·(2ⁿ-1) = 5·31 = 155 |
| 단위 커패시터 (C) | **4.9 fF** | kT/C 노이즈 요구 기준 설계 |
| MSB CDAC 총 용량 | 668 fF (CP3 포함) | |
| 소자 타입 | **Shielded MOM cap** | 7금속 레이어, 최소 피치 100nm |

```
[구조]
LSB CDAC (5b) ──VX──[6C bridge]──VOUT── MSB CDAC (7b)
                    ↑
              X·C redundant cap (155C)
              6b gain calibration CDAC (63C)
```

---

## 핵심 수식

### 출력 전압 (이상적)
```
ΔVOUT[NMSB, NLSB] = ALSB · (2ⁿ·NMSB + NLSB)

ALSB = VDD / [2^(m+n) + (Y-1)·(2ⁿ-1) - 1]
     = VDD / [4096 + 155 - 1]
     = VDD / 4250   ← 이상적 1LSB 전압

최대 출력: ALSB · (2¹² - 1) ≈ 0.964 · VDD   (Y=6, m=7 기준)
```

> ※ Y=0 (이상적 binary-weighted)일 때 ALSB = VDD/4095 ≈ VDD/2¹²
> Y=6이면 분모가 4250으로 증가 → 최대 출력 전압 범위 약 3.6% 감소

### 선형성 조건
```
X = (Y-1)·(2ⁿ-1)   → 이론적 무한 선형성 보장
기생 포함 시: X + P1 = (2ⁿ-1)·(Y + P2 - 1)
```

### 기생 민감도
```
ΔINLMAX/ΔP1 = 1/(Y + P2)       → Y 클수록 감소 (6× 개선)
ΔINLMAX/ΔP2 = -(2ⁿ-1)/(Y+P2)² → n 작을수록 유리
```

---

## 커패시터 배열 (MOM)

- 구조: 1D 배열, 완전 Common-centroid 라우팅
- 쉴딩: M1, M7 레이어로 VX, VOUT 노드 보호
- Guard metal: MSB에서는 VOUT에 연결 (CP3 최소화)
- 추출된 기생: VX 노드 CP1 = **20.5C** → 실제 redundant cap = 91C로 조정 (post-layout)
- CDAC 크기: **59 × 29 μm** (dummy 포함)

---

## 측정 결과

| 항목 | 값 |
|------|----|
| INL / DNL | **< 1.2 LSB / < 0.8 LSB** (21칩 동일 코드) |
| SNDR (Nyquist) | **57.8 dB** (ENOB 9.31b) |
| SFDR (Nyquist) | 71.18 dBc |
| 소비전력 | **0.61 μW** |
| 면적 | **0.013 mm²** |
| FOMw | 9.6 fJ/conversion-step |
| CDAC 보정 | Fixed gain calibration code (1회, 칩별 동일) |

---

## 우리 설계 적용 포인트

1. **CDAC output 전압 범위**: 0 ~ 0.964·VDD (12b, Y=6 기준)
   - LSB 전압: VDD/4250 ≈ 0.212mV @ VDD=0.9V
2. **C₃ 경계 조건**: CDAC output이 V₃ 노드의 하단 플레이트 구동
   - Step 응답 시 CDAC code 고정 → V₃ = CDAC_OUT = 상수
   - mid-scale code (2047): VOUT ≈ 0.482·VDD
3. **C₃ 값**: 이론상 C2의 절반 → C₃ ≈ C2/2 ≈ **0.56 pF** (C2=1.12pF 기준)
4. **온도 의존성**: MOM 커패시터 TCC — 65nm 기준 약 ±30ppm/°C 수준 (공정 의존)
5. **면적 참고**: 59×29μm → 28nm 스케일 시 추가 축소 가능
