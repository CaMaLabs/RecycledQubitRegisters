package main

// K201 is a conservative Go search accelerator. It never changes checkpoints.
// Python re-parses and proves every proposed rewrite before acceptance.
import (
 "bufio"
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "strings"
)

type Request struct { Lines []string `json:"lines"`; MaxWindows int `json:"max_windows"` }
type Proposal struct { Start int `json:"start"`; Stop int `json:"stop"`; Replacement []string `json:"replacement"`; Kind string `json:"kind"`; Scanned int `json:"scanned"` }
type Gate struct { op string; q []string; valid bool }
var arity=map[string]int{"X":1,"CX":2,"CCX":3,"SWAP":2,"CSWAP":3,"Z":1,"CZ":2,"CCZ":3,"S":1,"S_DAG":1,"T":1,"T_DAG":1}
var invol=map[string]bool{"X":true,"CX":true,"CCX":true,"SWAP":true,"CSWAP":true,"Z":true,"CZ":true,"CCZ":true}
func parse(s string) Gate {
 t:=strings.Fields(s); if len(t)==0{return Gate{}}
 n,ok:=arity[t[0]];if !ok||len(t)!=n+1{return Gate{}}
 seen:=map[string]bool{}
 for _,q:=range t[1:] {if len(q)<2||q[0]!='q'||seen[q]{return Gate{}};for _,c:=range q[1:] {if c<'0'||c>'9'{return Gate{}}};seen[q]=true}
 return Gate{t[0],t[1:],true}
}
func same(a,b Gate)bool {
 if !a.valid||!b.valid||a.op!=b.op||len(a.q)!=len(b.q){return false}
 // Control order may differ for symmetric gates; Python performs final proof.
 for i:=range a.q {if a.q[i]!=b.q[i]{return false}}
 return true
}
func disjoint(a,b Gate)bool {
 for _,x:=range a.q {for _,y:=range b.q {if x==y{return false}}};return true
}
func search(r Request)*Proposal {
 if r.MaxWindows<=0 {r.MaxWindows=len(r.Lines)}
 gs:=make([]Gate,len(r.Lines));for i,s:=range r.Lines{gs[i]=parse(s)}
 scanned:=0
 for i:=0;i<len(gs);i++ {
  if !gs[i].valid{continue}
  scanned++;if scanned>r.MaxWindows{break}
  // Cancel identical involutions separated only by gates on disjoint wires.
  for j:=i+1;j<len(gs)&&j<=i+64;j++ {
   if !gs[j].valid{break}
   if same(gs[i],gs[j])&&invol[gs[i].op] {
    replacement:=append([]string{},r.Lines[i+1:j]...)
    return &Proposal{i,j+1,replacement,"commuting_involution_cancel",scanned}
   }
   if !disjoint(gs[i],gs[j]){break}
  }
 }
 return nil
}
func main(){
 max:=flag.Int("max-bytes",32<<20,"maximum input bytes");flag.Parse()
 sc:=bufio.NewScanner(os.Stdin);sc.Buffer(make([]byte,64*1024),*max)
 if !sc.Scan(){fmt.Fprintln(os.Stderr,"missing JSON request");os.Exit(2)}
 var r Request;if err:=json.Unmarshal(sc.Bytes(),&r);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 enc:=json.NewEncoder(os.Stdout);if err:=enc.Encode(search(r));err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
}
