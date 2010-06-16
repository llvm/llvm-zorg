import math

def mean(l):
    return sum(l)/len(l)

def median(l):
    l = list(l)
    l.sort()
    N = len(l)
    return (l[(N-1)//2] + l[N//2])*.5

def median_absolute_deviation(l, med = None):
    if med is None:
        med = median(l)
    return median([abs(x - med) for x in l])

def standard_deviation(l):
    m = mean(l)
    means_sqrd = sum([(v - m)**2 for v in l]) / len(l)
    rms = math.sqrt(means_sqrd)
    return rms
