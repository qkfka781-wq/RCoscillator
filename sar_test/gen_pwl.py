#!/usr/bin/env python
# Generate ckr_asyn.pwl / adc_rst.pwl for SAR integration TB.
# Run IN the sim netlist dir so files land where file="..." looks:
#   cd /home1/sf3101/.../simulation/test_StrongARMfull/spectre/schematic/netlist/
#   python gen_pwl.py
Thalf=2e-6; Nhalf=20; Tsar=20e-9; Ncomp=14; guard=20e-9; edge=50e-12; duty=0.5   # Tsar=20n -> 50MHz (was 10n/100MHz: overshoot from settling)
hi=Tsar*duty
def w(pairs): return ''.join('%.12e %.3f\n'%(t,v) for t,v in pairs)
# CKR_ASYN: idle HIGH (1), goes LOW (0) for each of the 14 clock slots (active-low pulses).
# ADC_RST: idle LOW (0), positive pulse at the 15th slot.
ckr=[(0.0,1.0)]; rst=[(0.0,0.0)]
for k in range(Nhalf):
    b=k*Thalf+guard
    for i in range(Ncomp):
        t0=b+i*Tsar
        ckr += [(t0-edge,1.0),(t0,0.0),(t0+hi,0.0),(t0+hi+edge,1.0)]
    r=b+Ncomp*Tsar
    rst += [(r-edge,0.0),(r,1.0),(r+hi,1.0),(r+hi+edge,0.0)]
tend=Nhalf*Thalf
ckr.append((tend,1.0)); rst.append((tend,0.0))
for p,name in [(ckr,'ckr_asyn.pwl'),(rst,'adc_rst.pwl')]:
    bad=[i for i in range(1,len(p)) if p[i][0]<=p[i-1][0]]
    assert not bad, ('non-increasing at %d'%bad[0])
    open(name,'w').write(w(p))
    print('wrote %s (%d pts)'%(name,len(p)))
