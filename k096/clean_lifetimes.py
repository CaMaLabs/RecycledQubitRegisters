import re,heapq,sys,kickmix as km,collections
Q=re.compile(r'\bq(\d+)\b')
def compact(lines):
 reserved=set();scope=0;segments=[];active={};bind={};last={}
 for line in lines:
  if line.startswith('APPEND_TO_REGISTER'):reserved.update(map(int,Q.findall(line)))
 for i,line in enumerate(lines):
  op=line.split()[0] if line.strip() else '';qs=list(map(int,Q.findall(line)))
  if op=='PUSH_CONDITION':scope+=1
  if op=='POP_CONDITION':scope-=1
  for q in qs:
   if q in reserved:continue
   if q not in active:
    active[q]=len(segments);segments.append([i,i,q]);
   j=active[q];segments[j][1]=i;bind[i,q]=j
  if op=='HMR' and not scope and ' if ' not in line:
   active.pop(qs[0],None)
 end=len(lines)
 for q,j in active.items():segments[j][1]=end
 busy=[];free=[];nextq=len(reserved);ids={}
 assert reserved==set(range(nextq))
 for j,(start,stop,q) in sorted(enumerate(segments),key=lambda a:a[1][0]):
  while busy and busy[0][0]<start:
   _,x=heapq.heappop(busy);heapq.heappush(free,x)
  if free:x=heapq.heappop(free)
  else:x=nextq;nextq+=1
  ids[j]=x;heapq.heappush(busy,(stop,x))
 out=[]
 for i,line in enumerate(lines):
  out.append(Q.sub(lambda m:'q'+str(int(m[1]) if int(m[1]) in reserved else ids[bind[i,int(m[1])]]),line))
 return out,{'qubits':nextq,'segments':len(segments)}
if __name__=='__main__':
 out,s=compact(open(sys.argv[1]).readlines());print(s);open(sys.argv[2],'w').writelines(out)
