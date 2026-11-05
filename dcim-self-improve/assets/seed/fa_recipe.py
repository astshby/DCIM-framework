"""Independent22T full-adder diffusion-chain coverage, not drawn geometry."""
import json
from core_geometry import OLD
from seed_config import digest


def recipe():
    path = OLD/"fa22t12_v1_layout_v2_lvs/source.cdl"
    ds = {}
    for line in path.read_text().splitlines():
        f = line.split()
        if f and f[0].startswith("M_"):
            ds[f[0]] = dict(nodes=f[1:5],model=f[5],params=dict(x.split("=") for x in f[6:]))
    specs = [
        ("xor_n", [0,1], ["A","PROP","B_BAR"]),
        ("xor_p", [11,12], ["A","PROP","B"]),
        ("inv_n", [2,3], ["B_BAR","VSS","PROP_BAR"]),
        ("inv_p", [13,14], ["B_BAR","VDD","PROP_BAR"]),
        ("sum_n", [4,5], ["PROP","SUM_BAR","CI"]),
        ("sum_p", [15,16], ["PROP_BAR","SUM_BAR","CI"]),
        ("mux_n", [6,7], ["CI","CARRY_MUX","A"]),
        ("mux_p", [17,18], ["CI","CARRY_MUX","A"]),
        ("carry_inv_n", [8], ["CARRY_BAR","VSS"]),
        ("carry_inv_p", [19], ["CARRY_BAR","VDD"]),
        ("outputs_n", [9,10], ["CO","VSS","S"]),
        ("outputs_p", [20,21], ["CO","VDD","S"]),
    ]
    chains,used = [],[]
    for name,numbers,nets in specs:
        names = [f"M_M{i}" for i in numbers]
        selected = [ds[n] for n in names]
        assert len({(m["model"],m["params"]["L"],m["params"]["nfin"]) for m in selected}) == 1
        for i,m in enumerate(selected):
            assert {m["nodes"][0],m["nodes"][2]} == set(nets[i:i+2])
        chains.append(dict(name=name,devices=names,diffusion_nets=nets,
                           gate_nets=[m["nodes"][1] for m in selected],
                           model=selected[0]["model"],params=selected[0]["params"]))
        used.extend(names)
    assert sorted(used) == sorted(ds) and len(used) == 22
    return dict(state="independent_topology_checked_only",chains=chains,
                source=str(path),source_sha256=digest(path),
                sizing="unchangedv1 SVT2/4fin,L16nm",
                not_qualified=["native compact masks","seams","DRC/LVS","PEX functionality"],
                arithmetic="S=(A+B+CI)%2, CO=(A+B+CI)//2; no pipeline state")


if __name__ == "__main__":
    result = recipe()
    print(json.dumps(result, indent=2))
