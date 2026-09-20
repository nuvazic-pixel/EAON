from .constants import G,C,HBAR,PI
def evaporation_time(M0):
    if M0<=0: raise ValueError("M0>0 required")
    return 5120*PI*G**2*M0**3/(HBAR*C**4)
def mass_at_tau(M0,tau):
    if not 0<=tau<1: raise ValueError("0<=tau<1 required")
    return M0*(1-tau)**(1/3)
