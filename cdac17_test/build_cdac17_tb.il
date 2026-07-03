;; build_cdac17_tb.il  v1 -- CDAC_17b boundary/linearity TB (idempotent, ASCII, no setof)
;; load("/home1/sf3101/pdk_analog/CADENCE_ENV/0_BARAM/build_cdac17_tb.il")
;; buildCdac17TB("0_BARAM" "tset_CDAC17b" "CDAC_17b" 11 20e-9 20e-9)
;;   tbLib tbCell dutCell Ncount Tcode t_rst
;;   Ncount=11 -> sweep bits0..10 as binary counter (code 0..2047), bits11..16 held 0.
;;   Reveals segment boundaries: code 32 (VX->VM), code 1024 (VM->VOUT).
;;   Ideal analysis predicts NON-MONOTONIC drop at code 1024 (bit10) if caps non-binary.
;;
;; DUT CDAC_17b port: IN<16:0> VDD VM VOUT VSS VX  (3 floating nodes VOUT,VM,VX -> 3 reset SW)
;; plate = ~IN (cell INV) -> counter driven v1=1/v2=0 so plate follows increasing code.

procedure(tbTermPt(inst tname)
  let((res)
    foreach(mt inst~>master~>terminals
      when(mt~>name==tname
        res = dbTransformPoint(centerBox(car(mt~>pins)~>fig~>bBox) inst~>transform)))
    res))

procedure(tbSetCdf(cdf prompt val)
  foreach(fld cdf~>parameters
    when(fld~>prompt==prompt fld~>value = val)))

procedure(tbPin(cv inst tname netName dx dy)
  let((pt w)
    pt = tbTermPt(inst tname)
    when(pt
      w = schCreateWire(cv "route" "full"
            list(pt list(xCoord(pt)+dx yCoord(pt)+dy)) 0.0625 0.0625 0.0)
      schCreateWireLabel(cv car(w) list(xCoord(pt)+dx yCoord(pt)+dy)
        netName "lowerCenter" "R0" "stick" 0.0625 nil))))

procedure(tbInst(cv lib cell name loc)
  dbCreateInst(cv dbOpenCellViewByType(lib cell "symbol") name loc "R0"))

procedure(buildCdac17TB(tbLib tbCell dutCell @optional (Ncount 11) (Tcode 20e-9) (t_rst 20e-9))
  let((cv dut src vdd rst cdf k dly wid per sw)
    cv = dbOpenCellViewByType(tbLib tbCell "schematic" "schematic" "a")
    foreach(x cv~>instances dbDeleteObject(x))
    foreach(x cv~>shapes dbDeleteObject(x))

    dut = tbInst(cv tbLib dutCell "I0" list(8.0 0.0))
    tbPin(cv dut "IN<16:0>" "IN<16:0>" -1.0 0.0)
    tbPin(cv dut "VDD"  "VDD"  0.0  1.0)
    tbPin(cv dut "VOUT" "VOUT" 1.0  0.5)
    tbPin(cv dut "VM"   "VM"   1.0  0.0)
    tbPin(cv dut "VX"   "VX"   1.0 -0.5)
    tbPin(cv dut "VSS"  "VSS"  0.0 -1.0)

    ;; ---- counter sources IN<0..Ncount-1> (v1=1/v2=0, INV-corrected -> plate=code) ----
    for(k 0 Ncount-1
      dly = t_rst + expt(2.0 k)*Tcode
      wid = expt(2.0 k)*Tcode
      per = expt(2.0 k+1)*Tcode
      src = tbInst(cv "analogLib" "vpulse" sprintf(nil "V_IN%d" k) list(0.0 -2.0*k))
      cdf = cdfGetInstCDF(src)
      tbSetCdf(cdf "Voltage 1" "1")
      tbSetCdf(cdf "Voltage 2" "0")
      tbSetCdf(cdf "Period" sprintf(nil "%g" per))
      tbSetCdf(cdf "Delay time" sprintf(nil "%g" dly))
      tbSetCdf(cdf "Pulse width" sprintf(nil "%g" wid))
      tbSetCdf(cdf "Rise time" "10p")
      tbSetCdf(cdf "Fall time" "10p")
      tbPin(cv src "PLUS" sprintf(nil "IN<%d>" k) 0.5 0.0)
      tbPin(cv src "MINUS" "VSS" 0.0 -0.5))

    ;; ---- upper bits IN<Ncount..16> held = 1 (vdc) -> plate=0 (bit off) ----
    for(k Ncount 16
      src = tbInst(cv "analogLib" "vdc" sprintf(nil "V_HI%d" k) list(-4.0 -2.0*k))
      cdf = cdfGetInstCDF(src)
      tbSetCdf(cdf "DC voltage" "1")
      tbPin(cv src "PLUS" sprintf(nil "IN<%d>" k) 0.5 0.0)
      tbPin(cv src "MINUS" "VSS" 0.0 -0.5))

    ;; ---- VDD ----
    vdd = tbInst(cv "analogLib" "vdc" "V_VDD" list(16.0 4.0))
    cdf = cdfGetInstCDF(vdd)
    tbSetCdf(cdf "DC voltage" "1")
    tbPin(cv vdd "PLUS" "VDD" 0.5 0.0)
    tbPin(cv vdd "MINUS" "VSS" 0.0 -0.5)

    ;; ---- RST pulse: closed [0,t_rst] then open ----
    rst = tbInst(cv "analogLib" "vpulse" "V_RST" list(16.0 1.0))
    cdf = cdfGetInstCDF(rst)
    tbSetCdf(cdf "Voltage 1" "0")
    tbSetCdf(cdf "Voltage 2" "1")
    tbSetCdf(cdf "Delay time" "0")
    tbSetCdf(cdf "Pulse width" sprintf(nil "%g" t_rst))
    tbSetCdf(cdf "Period" "1")
    tbSetCdf(cdf "Rise time" "10p")
    tbSetCdf(cdf "Fall time" "10p")
    tbPin(cv rst "PLUS" "RST" 0.5 0.0)
    tbPin(cv rst "MINUS" "VSS" 0.0 -0.5)

    ;; ---- 3 reset switches: VOUT/VM/VX -> VSS, control RST ----
    foreach(pr list(list("SW_O" "VOUT" 5.0) list("SW_M" "VM" 1.0) list("SW_X" "VX" -3.0))
      sw = tbInst(cv "analogLib" "switch" car(pr) list(13.0 caddr(pr)))
      cdf = cdfGetInstCDF(sw)
      tbSetCdf(cdf "Closed resistance" "1")
      tbSetCdf(cdf "Open resistance" "1T")
      tbSetCdf(cdf "Threshold 1" "0.4")
      tbSetCdf(cdf "Threshold 2" "0.6")
      tbPin(cv sw "N+" cadr(pr) 0.5 0.0)
      tbPin(cv sw "N-" "VSS" 0.5 -0.3)
      tbPin(cv sw "NC+" "RST" 0.5 -0.6)
      tbPin(cv sw "NC-" "VSS" 0.5 -0.9))

    schCheck(cv)
    dbSave(cv)
    printf("buildCdac17TB done: %s/%s  (Ncount=%d Tcode=%g t_rst=%g, codes 0..%d)\n"
      tbLib tbCell Ncount Tcode t_rst (expt(2 Ncount)-1))
    cv))

printf("=== build_cdac17_tb v1 loaded ===\n")
