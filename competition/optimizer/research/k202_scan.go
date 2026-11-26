package main

// K202: read-only parallel CCX rewrite discovery; Python proves every proposal.
import (
 "bufio"
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "runtime"
 "sort"
 "strconv"
 "strings"
 "sync"
)
type Request struct { Lines []string `json:"lines"`; Workers int `json:"workers"`; MaxCandidates int `json:"max_candidates"` }
type Candidate struct { Start int `json:"start"`; Stop int `json:"stop"`; Replacement []string `json:"replacement"`; Method string `json:"method"`; CCXSaved int `json:"ccx_saved"` }
type Gate struct { op string; q []int; valid bool }
var arity=map[string]int{"X":1,"CX":2,"CCX":3,"SWAP":2,"CSWAP":3,"Z":1,"CZ":2,"CCZ":3,"S":1,"S_DAG":1,"T":1,"T_DAG":1}
func parse(s string)Gate{
 t:=strings.Fields(s);if len(t)==0{return Gate{}}
 n,ok:=arity[t[0]];if !ok||len(t)!=n+1{return Gate{}}
 q:=make([]int,n);seen:=map[int]bool{}
 for i,v:=range t[1:]{if len(v)<2||v[0]!='q'{return Gate{}};x,e:=strconv.Atoi(v[1:]);if e!=nil||x<0||seen[x]{return Gate{}};q[i]=x;seen[x]=true}
 return Gate{t[0],q,true}
}
func cx(a,b int)string{return fmt.Sprintf("CX q%d q%d\n",a,b)}
func ccx(a,b,t int)string{return fmt.Sprintf("CCX q%d q%d q%d\n",a,b,t)}
func controls(g Gate,a,b int)bool{return (g.q[0]==a&&g.q[1]==b)||(g.q[0]==b&&g.q[1]==a)}
func discover(g []Gate,i int)[]Candidate{
 if i+1>=len(g)||!g[i].valid||!g[i+1].valid{return nil}
 x,y:=g[i],g[i+1];out:=[]Candidate{}
 if x.op=="CCX"&&y.op=="CCX"&&x.q[2]==y.q[2]&&controls(y,x.q[0],x.q[1]){
  out=append(out,Candidate{i,i+2,[]string{},"adjacent_ccx_cancel",2})
 }
 if i+2>=len(g)||!g[i+2].valid{return out}
 z:=g[i+2]
 // CX(a,b) CCX(b,c,t) CX(a,b) == CCX(b,c,t) CCX(a,c,t)
 // Reverse direction reduces CCX count only if CCX pair occurs with CX.
 // Python exact basis-state proof is mandatory; Go never accepts its own claims.
 if x.op=="CCX"&&y.op=="CCX"&&z.op=="CX"&&x.q[2]==y.q[2]{
  a,b:=z.q[0],z.q[1]
  for _,pair:=range [][2]Gate{{x,y},{y,x}}{
   f,s:=pair[0],pair[1]
   for _,c:=range f.q[:2]{
    if controls(f,b,c)&&controls(s,a,c)&&a!=b&&a!=c&&b!=c&&x.q[2]!=a&&x.q[2]!=b&&x.q[2]!=c{
     out=append(out,Candidate{i,i+3,[]string{cx(a,b),ccx(b,c,x.q[2])},"ccx_affine_conjugation",1})
    }
   }
  }
 }
 if x.op=="CX"&&y.op=="CCX"&&z.op=="CCX"&&y.q[2]==z.q[2]{
  a,b:=x.q[0],x.q[1]
  for _,pair:=range [][2]Gate{{y,z},{z,y}}{
   f,s:=pair[0],pair[1]
   for _,c:=range f.q[:2]{
    if controls(f,b,c)&&controls(s,a,c)&&a!=b&&a!=c&&b!=c&&y.q[2]!=a&&y.q[2]!=b&&y.q[2]!=c{
     out=append(out,Candidate{i,i+3,[]string{ccx(b,c,y.q[2]),cx(a,b)},"ccx_affine_conjugation",1})
    }
   }
  }
 }
 return out
}
func main(){
 workers:=flag.Int("workers",runtime.NumCPU(),"parallel scan workers")
 limit:=flag.Int("max-candidates",256,"maximum proposals");flag.Parse()
 sc:=bufio.NewScanner(os.Stdin);sc.Buffer(make([]byte,65536),64<<20)
 if !sc.Scan(){fmt.Fprintln(os.Stderr,"expected JSON request");os.Exit(2)}
 var r Request;if err:=json.Unmarshal(sc.Bytes(),&r);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 if r.Workers>0{*workers=r.Workers};if r.MaxCandidates>0{*limit=r.MaxCandidates}
 if *workers<1{*workers=1};if *workers>128{*workers=128};if *limit<1{*limit=1}
 g:=make([]Gate,len(r.Lines));for i,s:=range r.Lines{g[i]=parse(s)}
 jobs:=make(chan int,1024);results:=make(chan Candidate,1024);var wg sync.WaitGroup
 for w:=0;w<*workers;w++{wg.Add(1);go func(){defer wg.Done();for i:=range jobs{for _,c:=range discover(g,i){results<-c}}}()}
 go func(){for i:=range g{jobs<-i};close(jobs);wg.Wait();close(results)}()
 all:=[]Candidate{};seen:=map[string]bool{}
 for c:=range results{key:=fmt.Sprintf("%d:%d:%s",c.Start,c.Stop,c.Method);if !seen[key]{seen[key]=true;all=append(all,c)}}
 sort.Slice(all,func(i,j int)bool{if all[i].CCXSaved!=all[j].CCXSaved{return all[i].CCXSaved>all[j].CCXSaved};return all[i].Start<all[j].Start})
 if len(all)>*limit{all=all[:*limit]}
 if err:=json.NewEncoder(os.Stdout).Encode(all);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
}
