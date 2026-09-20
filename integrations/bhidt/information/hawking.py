def hawking_branch(tau):
    if not 0<=tau<=1: raise ValueError
    return 1-(1-tau)**(2/3)
