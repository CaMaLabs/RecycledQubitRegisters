// Conservative streaming QRR lifetime / unused-wire audit on public DQI KMX.
// No input measurement or approximate gate rewrite. Original condition scopes
// are retained. Only unconditional HMR/R proves an end-of-live-value reset.
#include <algorithm>
#include <cctype>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <queue>
#include <set>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>
using namespace std;
struct Segment { uint64_t start,end; unsigned wire,physical=0; };
static vector<unsigned> qubits(const string& s) {
 vector<unsigned> q;
 for(size_t i=0;i<s.size();++i)if(s[i]=='q' && (i==0 || isspace((unsigned char)s[i-1])) && i+1<s.size() && isdigit((unsigned char)s[i+1])) {
  unsigned x=0; ++i; while(i<s.size() && isdigit((unsigned char)s[i])) { x=10*x+s[i]-'0';++i; } q.push_back(x);
 }
 return q;
}
int main(int argc,char**argv) {
 if(argc<3) { cerr<<"usage: dqi_lifetime_audit input.kmx report.json [output.kmx]\n";return 2; }
 ifstream f(argv[1]);if(!f){cerr<<"input unavailable\n";return 2;}
 string s;uint64_t line=0;int depth=0;set<unsigned> reserved,used;unordered_map<unsigned,size_t> active;vector<Segment> segments;unordered_map<string,uint64_t> counts;
 while(getline(f,s)) {
  auto end=s.find(' ');string op=s.substr(0,end);auto qs=qubits(s);for(auto q:qs)used.insert(q);counts[op]++;
  if(op=="APPEND_TO_REGISTER")for(auto q:qs)reserved.insert(q);
  for(auto q:qs) {
   if(!active.count(q)) {active[q]=segments.size();segments.push_back({line,line,q,0});}
   segments[active[q]].end=line;
  }
  if((op=="HMR"||op=="R")&&depth==0&&s.find(" if ")==string::npos&&!qs.empty())active.erase(qs[0]);
  if(op=="PUSH_CONDITION")depth++;if(op=="POP_CONDITION")depth--;if(depth<0){cerr<<"scope underflow\n";return 3;}
  ++line;
 }
 if(depth){cerr<<"unclosed scopes\n";return 3;}for(auto [q,i]:active)segments[i].end=line;
 unordered_map<unsigned,unsigned> inputmap;unsigned next=0;for(auto q:reserved)inputmap[q]=next++;
 vector<size_t> order;for(size_t i=0;i<segments.size();++i)if(!reserved.count(segments[i].wire))order.push_back(i);else segments[i].physical=inputmap[segments[i].wire];
 sort(order.begin(),order.end(),[&](size_t a,size_t b){return segments[a].start<segments[b].start;});
 using Item=pair<uint64_t,unsigned>;priority_queue<Item,vector<Item>,greater<Item>> busy;priority_queue<unsigned,vector<unsigned>,greater<unsigned>> free;
 unsigned peak=next;uint64_t peakline=0;
 for(auto i:order) {
  auto &v=segments[i];while(!busy.empty()&&busy.top().first<v.start){free.push(busy.top().second);busy.pop();}
  unsigned wire;if(free.empty())wire=next++;else{wire=free.top();free.pop();}v.physical=wire;busy.push({v.end,wire});
  if(reserved.size()+busy.size()>peak){peak=reserved.size()+busy.size();peakline=v.start+1;}
 }
 unsigned maxid=used.empty()?0:*used.rbegin()+1;
 ofstream report(argv[2]);report<<"{\"lines\":"<<line<<",\"unique_used_wires\":"<<used.size()<<",\"original_max_wire_plus_one\":"<<maxid<<",\"registered_quantum_wires\":"<<reserved.size()<<",\"scratch_segments\":"<<order.size()<<",\"conservative_colored_qubits\":"<<next<<",\"peak_live_wires\":"<<peak<<",\"peak_line\":"<<peakline<<",\"counts\":{";
 bool first=true;for(auto [op,n]:counts){if(!first)report<<',';first=false;report<<'"'<<op<<"\":"<<n;}report<<"},\"scope\":\"Unconditional reset splitting only; no branch algebra or rematerialization.\"}\n";report.close();
 cout<<"K099_DQI_LIFETIMES lines="<<line<<" used="<<used.size()<<" original="<<maxid<<" colored="<<next<<" registered="<<reserved.size()<<" scratch_segments="<<order.size()<<" peak="<<peak<<'\n';
 if(argc>3) {
  unordered_map<unsigned,vector<size_t>> bywire;for(size_t i=0;i<segments.size();++i)bywire[segments[i].wire].push_back(i);unordered_map<unsigned,size_t> cursor;ifstream source(argv[1]);ofstream out(argv[3]);line=0;
  while(getline(source,s)) {
   string rewritten;
   for(size_t i=0;i<s.size();) {
    if(s[i]=='q'&&(i==0||isspace((unsigned char)s[i-1]))&&i+1<s.size()&&isdigit((unsigned char)s[i+1])) {
     ++i;unsigned q=0;while(i<s.size()&&isdigit((unsigned char)s[i]))q=10*q+s[i++]-'0';unsigned mapped;
     if(reserved.count(q))mapped=inputmap[q];else {auto &list=bywire[q];auto &at=cursor[q];while(at+1<list.size()&&segments[list[at]].end<line)++at;mapped=segments[list[at]].physical;}rewritten+='q';rewritten+=to_string(mapped);
    }else rewritten+=s[i++];
   }
   out<<rewritten<<'\n';++line;
  }
 }
}
