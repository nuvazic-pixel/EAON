from .hawking import hawking_branch
from .island_qes import island_branch
def entropy_state(tau, model="ISLAND_QES"):
    h,i=hawking_branch(tau),island_branch(tau)
    if model=="HAWKING_SEMICLASSICAL":
        return {"radiation_entropy":h,"dominant_saddle":"NO_ISLAND","hawking":h,"island":i}
    if model!="ISLAND_QES": raise ValueError("unknown model")
    active=i<h
    return {"radiation_entropy":min(h,i),"dominant_saddle":"ISLAND" if active else "NO_ISLAND","hawking":h,"island":i}
def find_page_time():
    lo,hi=0.0,1.0
    for _ in range(100):
        mid=(lo+hi)/2
        if hawking_branch(mid)<island_branch(mid): lo=mid
        else: hi=mid
    return (lo+hi)/2
