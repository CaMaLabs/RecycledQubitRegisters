import re,sys,collections,itertools
Q=re.compile(r'\bq(\d+)\b');Z=frozenset();O=frozenset({frozenset()}); counter=itertools.count(22)
def fresh():return frozenset({frozenset({next(counter)})})
def mul(a,b):
 if len(a)*len(b)>4096:return fresh()
 out=set()
 for x in a:
  for y in b:
   v=x|y
   if v in out:out.remove(v)
   else:out.add(v)
 return frozenset(out) if len(out)<=256 else fresh()
def transform(lines):
 state={i:frozenset({frozenset({i})}) for i in range(22)};scope=0;stats=collections.Counter();out=[]
 def get(i):return state.get(i,Z)
 for line in lines:
  t=line.strip();op=t.split()[0] if t else '';q=list(map(int,Q.findall(t)));cond=(' if ' in t or scope>0)
  if op=='PUSH_CONDITION':scope+=1;out.append(line);continue
  if op=='POP_CONDITION':scope-=1;out.append(line);continue
  replacement=line
  if op in ('CX','CCX','X'):
   target=q[-1];value=O
   for c in q[:-1]:value=mul(value,get(c))
   if value==Z:replacement='';stats[op+'_zero']+=1
   elif not cond:
    if op=='CCX':
     a,b=map(get,q[:2]);r=None
     if a==O:r=q[1]
     elif b==O:r=q[0]
     elif a==b:r=q[0]
     if r is not None:replacement=f'CX q{r} q{target}\n';stats['CCX_to_CX']+=1
    state[target]=get(target)^value
    if len(state[target])>256:state[target]=fresh()
   else:
    state[target]=fresh()
  elif op in ('SWAP','CSWAP'):
   a,b=q[-2:];c=get(q[0]) if op=='CSWAP' else O
   if get(a)==get(b) or c==Z:replacement='';stats[op+'_redundant']+=1
   elif not cond:
    if c==O:
     state[a],state[b]=get(b),get(a)
     if op=='CSWAP':replacement=f'SWAP q{a} q{b}\n';stats['CSWAP_to_SWAP']+=1
    else:
     v=mul(c,get(a)^get(b));state[a]=get(a)^v;state[b]=get(b)^v
   else:state[a]=fresh();state[b]=fresh()
  elif op in ('CCZ','CZ','Z'):
   if any(get(c)==Z for c in q):replacement='';stats[op+'_zero']+=1
   else:
    remaining=[c for c in q if get(c)!=O]
    if len(remaining)<len(q):
     replacement=('NEG' if not remaining else {1:'Z',2:'CZ'}[len(remaining)]+' '+' '.join('q'+str(c) for c in remaining))+(' if '+t.split(' if ')[1] if ' if ' in t else '')+'\n';stats[op+'_reduced']+=1
  elif op=='HMR':
   state[q[0]]=fresh() if cond else Z
  elif op in ('Z_POW','S','T','S_DAG','T_DAG','NEG','BIT_INVERT','BIT_STORE0','BIT_STORE1','REGISTER','APPEND_TO_REGISTER') or not q:pass
  else:
   for c in q:state[c]=fresh()
  if replacement:out.append(replacement)
 return out,stats
if __name__=='__main__':
 out,stats=transform(open(sys.argv[1]).readlines());print(stats,flush=True);open(sys.argv[2],'w').writelines(out)
