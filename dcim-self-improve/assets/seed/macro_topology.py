"""Independent K8/C8/S8 macro connectivity; no layout-derived netlist.

All temporal requests/address/data are stable across a transaction. MASK=1
enables its channel's write. ADDR=16*term+row; unsupported upper address bits
disable transactions. EMA selects native delay taps, not22nm calibrated delay.
"""


def macro_netlist(channels=8):
    assert channels in (1,8)
    ports=[f"ADDR_{i}" for i in range(10)]
    ports+=["CLK","WEN","REN_GLOBAL","REN_LOCAL"]
    ports += [f"{name}_{i}" for name,count in
              (("D",4*channels),("Q",4*channels),("IFN",8),("SIGN",channels),("MASK",channels),
               ("EMA_RSA",2),("EMA_RWL",2),("PSUM",7*channels)) for i in range(count)]
    ports+=["VDDCM","VDDCLO","VSSC"]
    instances=[]
    def unit(c):
        return 96.0*(c%4),224.64*(c//4)
    def add(name,role,mapping,x,y,memory=False):
        assert "VDD" not in mapping and "VSS" not in mapping
        mapping=dict(mapping,VDD="VDDCM" if memory else "VDDCLO",VSS="VSSC")
        instances.append(dict(name=name,role=role,mapping=mapping,x=x,y=y))
    add("VALID","address_valid",{**{f"ADDR{i}":f"ADDR_{i}" for i in (3,7,8,9)},
                               "VALID":"ADDRESS_VALID"},
        unit(3)[0]+64.80 if channels==8 else 52.80,-104.64 if channels==8 else 48.)
    cm={n:n for n in "CLK WEN REN_GLOBAL REN_LOCAL PCH WCLK RCLK CRD CRDB GSEL WL_EN".split()}
    cm["VALID"]="ADDRESS_VALID"
    cm.update({f"EMA_{kind}{i}":f"EMA_{kind}_{i}" for kind in ("RSA","RWL") for i in range(2)})
    add("CTRL","controller",cm,64.80 if channels==8 else 52.80,-104.64)
    for which,offset,en,c in (("ROW",0,"WL_EN",1),("TERM",4,"GSEL",2)):
        mapping={f"A{i}":f"ADDR_{i+offset}" for i in range(3)}
        mapping.update(EN=en,**{f"Y{i}":f"{which}_{i}" for i in range(8)})
        add("DEC_"+which,"decoder",mapping,
            unit(c)[0]+64.80 if channels==8 else 76.80,
            -104.64 if channels==8 else 60.48+28.8*(c-1))
    for t in range(8):
        mapping={f"ROW{r}":f"ROW_{r}" for r in range(8)}
        mapping.update(SEL=f"TERM_{t}",LOCAL="REN_LOCAL",CRD="CRD",PCH="PCH")
        mapping.update({f"WL{r}":f"WL_{t}_{r}" for r in range(8)})
        mapping.update(LSEL=f"SEL_{t}",LSELB=f"SELB_{t}",
                       LCRD=f"CRD_{t}",LCRDB=f"CRDB_{t}",LPCH=f"PCH_{t}")
        ux,uy=unit(t)
        add(f"TD{t}","term_driver",mapping,
            ux+64.80 if channels==8 else 76.80,
            uy-48. if channels==8 else -88.32+16.32*t)
    for c in range(channels):
        ux,uy=unit(c)
        add(f"CD{c}","channel_driver",
            dict(MASK=f"MASK_{c}",WCLK="WCLK",RCLK="RCLK",PCH="PCH",
                 WE=f"WE_{c}",WEB=f"WEB_{c}",LRCLK=f"RCLK_{c}",LPCH=f"IOPCH_{c}"),
            ux,uy-104.64)
        for b in range(4):
            add(f"IO{c}_{b}","global_io",
                dict(D=f"D_{4*c+b}",Q=f"Q_{4*c+b}",GBL=f"GBL_{c}_{b}",GBLB=f"GBLB_{c}_{b}",
                     WE=f"WE_{c}",WEB=f"WEB_{c}",RCLK=f"RCLK_{c}",PCH=f"IOPCH_{c}"),
                ux+21.60*(b%2),uy-88.32+11.52*(b//2),memory=True)
        for t in range(8):
            mapping={f"WL{r}":f"WL_{t}_{r}" for r in range(8)}
            mapping.update({f"{p}{b}":f"{p}_{c}_{b}" for b in range(4) for p in ("GBL","GBLB")})
            mapping.update({f"PP{b}":f"P_{t}_{c}_{b}" for b in range(4)})
            mapping.update(SEL=f"SEL_{t}",SELB=f"SELB_{t}",PCH=f"PCH_{t}",
                           CRD=f"CRD_{t}",CRDB=f"CRDB_{t}",IFN=f"IFN_{t}")
            add(f"PS{t}_{c}","product_slice",mapping,
                ux+32.40*(t%2),uy+24.96*(t//2),memory=True)
        mapping={f"P{t}_{b}":f"P_{t}_{c}_{b}" for t in range(8) for b in range(4)}
        mapping.update(SIGN=f"SIGN_{c}",**{f"S{b}":f"PSUM_{7*c+b}" for b in range(7)})
        add(f"RED{c}","reduction",mapping,ux+12.,uy-56.64)
    assert len(instances)==12+14*channels
    return ports,instances


def arithmetic(weights,ifn,sign):
    """Independent integer evaluator; weights indexed[term][channel]."""
    return [sum((weights[t][c]-16 if (sign>>c)&1 and weights[t][c]>=8 else weights[t][c])
                for t in range(8) if not ((ifn>>t)&1))&127 for c in range(len(weights[0]))]
