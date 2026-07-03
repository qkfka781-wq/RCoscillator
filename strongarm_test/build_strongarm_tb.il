;; build_strongarm_tb.il  v1 -- SAR StrongARM comparator standalone TB (idempotent, ASCII, no setof)
;; load("/home1/sf3101/pdk_analog/CADENCE_ENV/0_BARAM/build_strongarm_tb.il")
;; buildStrongarmTB("0_BARAM" "TEST_StrongARM_STD" "StrongARM")
;;   optional args: Tclk delta Tdiff Tcm CMlo CMhi
;;   defaults:      3.333e-9 5e-3 1.667e-6 20e-6 0.2 0.8
;;
;; Method: clocked comparator + slow differential triangle (V_DIFF) + very-slow CM triangle (V_CM).
;;   Tclk << Tdiff << Tcm  -> one tran samples (CM, vdiff, decision) over the whole CM range.
;;   V_DIFF is referenced to VINN (PLUS=VINP, MINUS=VINN) so it injects differential only.
;;   Export time,VINP,VINN,CLK,OUT ; slice at each CLK rising edge.
;;
;; DUT port order: CLK OUT OUTB VDD VINN VINP VSS
;;   CLK high = eval (tail on), CLK low = precharge/reset. Offset handled by DLF later (not here).

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

procedure(buildStrongarmTB(tbLib tbCell dutCell @optional
    (Tclk 3.333e-9) (delta 5e-3) (Tdiff 1.667e-6) (Tcm 20e-6) (CMlo 0.2) (CMhi 0.8))
  let((cv dut vdd vcm vdi vck gnd cdf)
    cv = dbOpenCellViewByType(tbLib tbCell "schematic" "schematic" "a")
    foreach(x cv~>instances dbDeleteObject(x))
    foreach(x cv~>shapes dbDeleteObject(x))

    ;; ---- DUT ----
    dut = tbInst(cv tbLib dutCell "I0" list(8.0 0.0))
    tbPin(cv dut "CLK"  "CLK"  -1.0  0.5)
    tbPin(cv dut "VINP" "VINP" -1.0  0.0)
    tbPin(cv dut "VINN" "VINN" -1.0 -0.5)
    tbPin(cv dut "OUT"  "OUT"   1.0  0.5)
    tbPin(cv dut "OUTB" "OUTB"  1.0 -0.5)
    tbPin(cv dut "VDD"  "VDD"   0.0  1.0)
    tbPin(cv dut "VSS"  "VSS"   0.0 -1.0)

    ;; ---- VDD = 1 ----
    vdd = tbInst(cv "analogLib" "vdc" "V_VDD" list(16.0 3.0))
    cdf = cdfGetInstCDF(vdd)
    tbSetCdf(cdf "DC voltage" "1")
    tbPin(cv vdd "PLUS" "VDD" 0.5 0.0)
    tbPin(cv vdd "MINUS" "VSS" 0.0 -0.5)

    ;; ---- ground on VSS (global 0) ----
    gnd = tbInst(cv "analogLib" "gnd" "G0" list(16.0 -3.0))
    tbPin(cv gnd "gnd!" "VSS" 0.0 0.5)

    ;; ---- V_CM : slow triangle CMlo<->CMhi, PLUS=VINN MINUS=VSS ----
    vcm = tbInst(cv "analogLib" "vpulse" "V_CM" list(0.0 4.0))
    cdf = cdfGetInstCDF(vcm)
    tbSetCdf(cdf "Voltage 1"   sprintf(nil "%g" CMlo))
    tbSetCdf(cdf "Voltage 2"   sprintf(nil "%g" CMhi))
    tbSetCdf(cdf "Delay time"  "0")
    tbSetCdf(cdf "Rise time"   sprintf(nil "%g" Tcm/2.0))
    tbSetCdf(cdf "Fall time"   sprintf(nil "%g" Tcm/2.0))
    tbSetCdf(cdf "Pulse width" "0")
    tbSetCdf(cdf "Period"      sprintf(nil "%g" Tcm))
    tbPin(cv vcm "PLUS" "VINN" 0.5 0.0)
    tbPin(cv vcm "MINUS" "VSS" 0.0 -0.5)

    ;; ---- V_DIFF : fast triangle -delta<->+delta, PLUS=VINP MINUS=VINN (differential only) ----
    vdi = tbInst(cv "analogLib" "vpulse" "V_DIFF" list(0.0 0.0))
    cdf = cdfGetInstCDF(vdi)
    tbSetCdf(cdf "Voltage 1"   sprintf(nil "%g" -delta))
    tbSetCdf(cdf "Voltage 2"   sprintf(nil "%g" delta))
    tbSetCdf(cdf "Delay time"  "0")
    tbSetCdf(cdf "Rise time"   sprintf(nil "%g" Tdiff/2.0))
    tbSetCdf(cdf "Fall time"   sprintf(nil "%g" Tdiff/2.0))
    tbSetCdf(cdf "Pulse width" "0")
    tbSetCdf(cdf "Period"      sprintf(nil "%g" Tdiff))
    tbPin(cv vdi "PLUS" "VINP" 0.5 0.0)
    tbPin(cv vdi "MINUS" "VINN" 0.0 -0.5)

    ;; ---- V_CLK : comparison clock, PLUS=CLK MINUS=VSS ----
    vck = tbInst(cv "analogLib" "vpulse" "V_CLK" list(0.0 -4.0))
    cdf = cdfGetInstCDF(vck)
    tbSetCdf(cdf "Voltage 1"   "0")
    tbSetCdf(cdf "Voltage 2"   "1")
    tbSetCdf(cdf "Delay time"  "0")
    tbSetCdf(cdf "Rise time"   "10p")
    tbSetCdf(cdf "Fall time"   "10p")
    tbSetCdf(cdf "Pulse width" sprintf(nil "%g" Tclk/2.0))
    tbSetCdf(cdf "Period"      sprintf(nil "%g" Tclk))
    tbPin(cv vck "PLUS" "CLK" 0.5 0.0)
    tbPin(cv vck "MINUS" "VSS" 0.0 -0.5)

    schCheck(cv)
    dbSave(cv)
    printf("buildStrongarmTB done: %s/%s  (Tclk=%g delta=%g Tdiff=%g Tcm=%g CM=%g..%g)\n"
      tbLib tbCell Tclk delta Tdiff Tcm CMlo CMhi)
    cv))

printf("=== build_strongarm_tb v1 loaded ===\n")
