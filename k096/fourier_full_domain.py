#!/usr/bin/env python3
"""LWE/Walsh transform transfer: full 22-bit phase-spectrum sparsification.
Numerical architecture screen only. No verifier PASS or circuit is implied.
Zero-Toffoli parity phases are useful only if few rotations meet ALL x tolerances.
"""
import argparse,json,time
from pathlib import Path
import numpy as np

def fwht(a):
 a=np.asarray(a,dtype=float).copy();n=len(a);step=1
 while step<n:
  v=a.reshape(-1,2*step);left=v[:,:step].copy();right=v[:,step:].copy();v[:,:step]=left+right;v[:,step:]=left-right;step*=2
 return a

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 n=1<<22;maximum=3133452;x=np.arange(1,n,dtype=float);target=1/np.sqrt(x);tol=2**-24*target[:maximum];records=[];started=time.monotonic()
 for extension in ('zero','smooth'):
  for phase_one in (0.,1.):
   f=np.zeros(n);f[1:]=target
   if extension=='zero':f[maximum+1:]=0
   f[1]=phase_one
   coeff=fwht(f)/n;order=np.argsort(np.abs(coeff[1:]))[::-1]+1
   for keep in (41,128,512,1024,4096,16384,65536):
    sparse=np.zeros(n);sparse[0]=coeff[0];ind=order[:keep];sparse[ind]=coeff[ind];approx=fwht(sparse);approx-=approx[0]
    error=(approx[1:maximum+1]-target[:maximum]+.5)%1-.5;ratio=np.abs(error)/tol;worst=int(ratio.argmax());r={'extension':extension,'phase_x1':phase_one,'rotations':keep,'worst_error_over_tolerance':float(ratio[worst]),'worst_x':worst+1,'numerical_pass':bool(np.all(ratio<=1))};records.append(r);print('K096_FOURIER',json.dumps(r),flush=True)
 (a.out/'fourier_screen.json').write_text(json.dumps({'records':records,'elapsed_s':time.monotonic()-started,'status':'NUMERIC_SCREEN_ONLY','convention':'parity rotation exponent -4*Walsh coefficient, plus restored zero-input gauge; invalid input extension varied'},indent=2))
if __name__=='__main__':main()
