package main
// K203: bounded commutation-aware candidate discovery. All candidates require Python exact proof.
import("bufio";"encoding/json";"flag";"fmt";"os";"runtime";"sort";"strconv";"strings";"sync")
type Req struct{Lines []string `json:"lines"`;Workers int `json:"workers"`;MaxCandidates int `json:"max_candidates"`;MaxGap int `json:"max_gap"`}
type Cand struct{Start int `json:"start"`;Stop int `json:"stop"`;Replacement []string `json:"replacement"`;Method string `json:"method"`;CCXSaved int `json:"ccx_saved"`}
type Gate struct{op string;q []int;valid bool}
var arity=map[string]int{"X":1,"CX":2,"CCX":3,"SWAP":2,"CSWAP":3,"Z":1,"CZ":2,"CCZ":3,"S":1,"S_DAG":1,"T":1,"T_DAG":1}
var invol=map[string]bool{"X":true,"CX":true,"CCX":true,"SWAP":true,"CSWAP":true,"Z":true,"CZ":true,"CCZ":true}
func parse(s string)Gate{t:=strings.Fields(s);if len(t)==0{return Gate{}};n,ok:=arity[t[0]];if !ok||len(t)!=n+1{return Gate{}};q:=make([]int,n);seen:=map[int]bool{};for i,v:=range t[1:]{if len(v)<2||v[0]!='q'{return Gate{}};x,e:=strconv.Atoi(v[1:]);if e!=nil||x<0||seen[x]{return Gate{}};q[i]=x;seen[x]=true};return Gate{t[0],q,true}}
func same(a,b Gate)bool{if !a.valid||!b.valid||a.op!=b.op||len(a.q)!=len(b.q){return false};for i:=range a.q{if a.q[i]!=b.q[i]{return false}};return true}
func disjoint(a,b Gate)bool{for _,x:=range a.q{for _,y:=range b.q{if x==y{return false}}};return true}
func diagonal(g Gate)bool{switch g.op{case "Z","CZ","CCZ","S","S_DAG","T","T_DAG":return true};return false}
func target(g Gate)int{if g.op=="X"||g.op=="CX"||g.op=="CCX"{return g.q[len(g.q)-1]};return -1}
func commute(a,b Gate)bool{
 if !a.valid||!b.valid{return false}
 if disjoint(a,b)||diagonal(a)&&diagonal(b){return true}
 ta,tb:=target(a),target(b)
 if ta>=0&&tb>=0{
  for _,x:=range a.q[:len(a.q)-1]{if x==tb{return false}}
  for _,x:=range b.q[:len(b.q)-1]{if x==ta{return false}}
  return true
 }
 return false
}
func scan(g []Gate,lines []string,i,gap int)[]Cand{
 if !g[i].valid||!invol[g[i].op]{return nil}
 out:=[]Cand{}
 for j:=i+1;j<len(g)&&j<=i+gap+1;j++{
  if !g[j].valid{break}
  if same(g[i],g[j]){
   repl:=append([]string{},lines[i+1:j]...)
   saved:=0;if g[i].op=="CCX"{saved=2}
   out=append(out,Cand{i,j+1,repl,"commuting_involution_cancel",saved})
   break
  }
  if !commute(g[i],g[j]){break}
 }
 return out
}
func main(){
 workers:=flag.Int("workers",runtime.NumCPU(),"parallel workers");max:=flag.Int("max-candidates",1000,"candidate cap");gap:=flag.Int("max-gap",64,"max intervening gates");flag.Parse()
 sc:=bufio.NewScanner(os.Stdin);sc.Buffer(make([]byte,65536),128<<20);if !sc.Scan(){fmt.Fprintln(os.Stderr,"missing JSON");os.Exit(2)}
 var r Req;if e:=json.Unmarshal(sc.Bytes(),&r);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 if r.Workers>0{*workers=r.Workers};if r.MaxCandidates>0{*max=r.MaxCandidates};if r.MaxGap>0{*gap=r.MaxGap}
 if *workers<1{*workers=1};if *workers>128{*workers=128};if *gap<1{*gap=1};if *gap>512{*gap=512};if *max<1{*max=1}
 gs:=make([]Gate,len(r.Lines));for i,s:=range r.Lines{gs[i]=parse(s)}
 jobs:=make(chan int,1024);results:=make(chan Cand,1024);var wg sync.WaitGroup
 for k:=0;k<*workers;k++{wg.Add(1);go func(){defer wg.Done();for i:=range jobs{for _,c:=range scan(gs,r.Lines,i,*gap){results<-c}}}()}
 go func(){for i:=range gs{jobs<-i};close(jobs);wg.Wait();close(results)}()
 all:=[]Cand{};for c:=range results{all=append(all,c)}
 sort.Slice(all,func(i,j int)bool{if all[i].CCXSaved!=all[j].CCXSaved{return all[i].CCXSaved>all[j].CCXSaved};return all[i].Start<all[j].Start})
 if len(all)>*max{all=all[:*max]}
 if e:=json.NewEncoder(os.Stdout).Encode(all);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
}
