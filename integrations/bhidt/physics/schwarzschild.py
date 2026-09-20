from .constants import G,C,HBAR,K_B,PI
def schwarzschild_radius(M):
    if M<=0: raise ValueError("M>0 required")
    return 2*G*M/C**2
def hawking_temperature(M):
    if M<=0: raise ValueError("M>0 required")
    return HBAR*C**3/(8*PI*G*M*K_B)
def bekenstein_hawking_entropy(M):
    r=schwarzschild_radius(M); A=4*PI*r*r
    return K_B*C**3*A/(4*G*HBAR)
