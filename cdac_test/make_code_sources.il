;; ============================================================
;;  make_code_sources.il
;;  CDAC_12b 검증용 IN<11:0> 코드소스(vpulse ×12) 자동 생성
;;  이진카운터 트릭: bit k → delay=t_rst+2^k*Tcode, width=2^k*Tcode,
;;                   period=2^(k+1)*Tcode  (V1=1/V2=0 = INV보정 → plate=정코드)
;;
;;  사용법 (CIW):
;;    load("cdac_test/make_code_sources.il")
;;    createCdacCodeSources("0_BARAM" "tset_CDAC12b" 12 10e-9 10e-9)
;;      libName cellName Nbit Tcode t_rst
;;  → 스키매틱에 V_IN0..V_IN11 배치, PLUS=IN<k> 라벨 / MINUS=VSS 라벨.
;;  ※ CDF 값은 "화면 라벨(prompt)"로 매칭해 세팅 → 내부 필드명 추측 불필요.
;; ============================================================

;; 터미널 절대좌표 = 마스터 핀점을 인스턴스 transform으로 변환 (instTerm엔 ~>fig 없음!)
procedure(termPt(inst tname)
  let((mt pinFig)
    mt = car(setof(t inst~>master~>terminals t~>name==tname))
    when(mt
      pinFig = car(mt~>pins)~>fig
      when(pinFig
        dbTransformPoint(centerBox(pinFig~>bBox) inst~>transform)))))

;; CDF 파라미터를 "prompt(화면라벨)"로 찾아 값 설정
procedure(setCdfByPrompt(cdf prompt val)
  let((fld)
    fld = car(setof(f cdf~>parameters f~>prompt==prompt))
    if(fld
      then fld~>value = val
      else printf("  WARN: CDF prompt '%s' 못찾음\n" prompt))))

;; PLUS/MINUS 에 짧은 wire + net 라벨
procedure(stubLabel(cv pt dx dy name)
  let((w)
    w = schCreateWire(cv "route" "full"
          list(pt list(xCoord(pt)+dx yCoord(pt)+dy)) 0.0625 0.0625 0.0)
    schCreateWireLabel(cv car(w)
      list(xCoord(pt)+dx yCoord(pt)+dy) name "lowerCenter" "R0" "stick" 0.0625 nil)))

procedure(createCdacCodeSources(libName cellName @optional (Nbit 12) (Tcode 10e-9) (t_rst 10e-9))
  let((cv inst cdf k dly wid per pPt mPt)
    cv = dbOpenCellViewByType(libName cellName "schematic" "schematic" "a")

    for(k 0 Nbit-1
      dly = t_rst + expt(2.0 k)*Tcode
      wid = expt(2.0 k)*Tcode
      per = expt(2.0 k+1)*Tcode

      inst = dbCreateInst(cv
               dbOpenCellViewByType("analogLib" "vpulse" "symbol")
               sprintf(nil "V_IN%d" k)
               list(0.0  -2.0*k)
               "R0")

      cdf = cdfGetInstCDF(inst)
      setCdfByPrompt(cdf "Voltage 1"   "1")                     ; rest=VDD (INV보정)
      setCdfByPrompt(cdf "Voltage 2"   "0")                     ; pulse=0
      setCdfByPrompt(cdf "Period"      sprintf(nil "%g" per))
      setCdfByPrompt(cdf "Delay time"  sprintf(nil "%g" dly))
      setCdfByPrompt(cdf "Pulse width" sprintf(nil "%g" wid))
      setCdfByPrompt(cdf "Rise time"   "10p")
      setCdfByPrompt(cdf "Fall time"   "10p")

      pPt = termPt(inst "PLUS")
      mPt = termPt(inst "MINUS")
      when(pPt stubLabel(cv pPt  0.5 0.0 sprintf(nil "IN<%d>" k)))  ; PLUS → IN<k>
      when(mPt stubLabel(cv mPt  0.0 -0.5 "VSS"))                   ; MINUS → VSS
    ) ; for

    schCheck(cv)
    dbSave(cv)
    printf("createCdacCodeSources: %s/%s 에 vpulse %d개 생성 완료\n" libName cellName Nbit)
    cv
  ))
