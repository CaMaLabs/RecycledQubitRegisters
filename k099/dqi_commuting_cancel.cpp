// Native streaming port of QRR A110-style control-aware involution cancellation.
// Conditions, measurements, classical writes and metadata are hard barriers.
#include <algorithm>
#include <array>
#include <cctype>
#include <cstdint>
#include <deque>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>
using namespace std;
struct Gate {string text,op;vector<unsigned> q;bool alive=true;};
static bool parse(const string&s,Gate&g){
 if(s.find(" if ")!=string::npos)return false;istringstream in(s);in>>g.op;int n=0;
 if(g.op=="X"||g.op=="Z")n=1;else if(g.op=="CX"||g.op=="CZ"||g.op=="SWAP")n=2;else if(g.op=="CCX"||g.op=="CCZ"||g.op=="CSWAP")n=3;else return false;
 string token;while(in>>token){if(token.size()<2||token[0]!='q'||!isdigit((unsigned char)token[1]))return false;g.q.push_back(stoul(token.substr(1)));}if((int)g.q.size()!=n)return false;
 auto copy=g.q;sort(copy.begin(),copy.end());if(unique(copy.begin(),copy.end())!=copy.end())return false;
 if(g.op=="CZ"||g.op=="CCZ"||g.op=="SWAP")sort(g.q.begin(),g.q.end());if(g.op=="CCX"&&g.q[0]>g.q[1])swap(g.q[0],g.q[1]);if(g.op=="CSWAP"&&g.q[1]>g.q[2])swap(g.q[1],g.q[2]);g.text=s;return true;
}
static bool intersects(const vector<unsigned>&a,const vector<unsigned>&b){for(auto x:a)for(auto y:b)if(x==y)return true;return false;}
static bool diag(const Gate&g){return g.op=="Z"||g.op=="CZ"||g.op=="CCZ";}
static bool xorgate(const Gate&g){return g.op=="X"||g.op=="CX"||g.op=="CCX";}
static bool commutes(const Gate&a,const Gate&b){
 if(!intersects(a.q,b.q))return true;if(a.op==b.op&&a.q==b.q)return true;if(diag(a)&&diag(b))return true;
 if(xorgate(a)&&xorgate(b)){
  for(size_t i=0;i+1<b.q.size();++i)if(a.q.back()==b.q[i])return false;
  for(size_t i=0;i+1<a.q.size();++i)if(b.q.back()==a.q[i])return false;return true;
 }
 if(diag(a)&&xorgate(b)){for(auto x:a.q)if(x==b.q.back())return false;return true;}
 if(diag(b)&&xorgate(a)){for(auto x:b.q)if(x==a.q.back())return false;return true;}
 return false;
}

static pair<unsigned,unsigned> apply_gate(const Gate&g,unsigned v){
 unsigned phase=0;auto q=g.q;
 if(g.op=="X")v^=1u<<q[0];
 else if(g.op=="CX")v^=((v>>q[0])&1u)<<q[1];
 else if(g.op=="CCX")v^=(((v>>q[0])&1u)&((v>>q[1])&1u))<<q[2];
 else if(g.op=="SWAP"||g.op=="CSWAP"){
  auto a=q[q.size()-2],b=q.back();if((g.op=="SWAP"||((v>>q[0])&1u))&&(((v>>a)&1u)!=((v>>b)&1u)))v^=(1u<<a)|(1u<<b);
 }else{phase=1;for(auto a:q)phase&=(v>>a)&1u;}
 return {v,phase};
}
static int selftest(){
 vector<Gate> gates;
 for(auto [name,n]:vector<pair<string,int>>{{"X",1},{"Z",1},{"CX",2},{"CZ",2},{"SWAP",2},{"CCX",3},{"CCZ",3},{"CSWAP",3}}){
  for(unsigned a=0;a<4;a++)for(unsigned b=0;b<(n>1?4u:1u);b++)for(unsigned c=0;c<(n>2?4u:1u);c++){
   if(n>1&&a==b)continue;if(n>2&&(a==c||b==c))continue;string line=name+" q"+to_string(a);if(n>1)line+=" q"+to_string(b);if(n>2)line+=" q"+to_string(c);Gate g;if(!parse(line,g))return 3;gates.push_back(g);
  }
 }
 uint64_t checked=0;
 for(auto&a:gates)for(auto&b:gates)if(commutes(a,b)){
  for(unsigned v=0;v<16;v++){
   auto x=apply_gate(a,v),y=apply_gate(b,x.first),z=apply_gate(b,v),w=apply_gate(a,z.first);
   if(y.first!=w.first||((x.second^y.second)!=(z.second^w.second)))return 4;
  }++checked;
 }
 Gate g;if(parse("CCX q0 q1 q2 if b0",g))return 5;
 cout<<"{\"status\":\"PASS\",\"commutation_pairs\":"<<checked<<",\"basis_states_each\":16,\"conditional_barrier\":true}\n";return 0;
}
int main(int argc,char**argv){if(argc==2&&string(argv[1])=="--self-test")return selftest();if(argc<4){cerr<<"usage: cancel input.kmx output.kmx report.json [window]\n";return 2;}ifstream in(argv[1]);ofstream out(argv[2]);if(!in||!out)return 2;size_t window=argc>4?stoul(argv[4]):2048;deque<Gate> pending;map<string,uint64_t> removed;uint64_t before=0,after=0;string line;
 auto flush=[&](size_t leave){while(pending.size()>leave){auto g=move(pending.front());pending.pop_front();if(g.alive){out<<g.text<<'\n';++after;}}};
 while(getline(in,line)){++before;Gate g;if(!parse(line,g)){flush(0);out<<line<<'\n';++after;continue;}bool hit=false;size_t steps=0;
  for(auto it=pending.rbegin();it!=pending.rend()&&steps<window;++it){if(!it->alive)continue;++steps;if(it->op==g.op&&it->q==g.q){it->alive=false;removed[g.op]+=2;hit=true;break;}if(!commutes(g,*it))break;}
  if(!hit)pending.push_back(move(g));if(pending.size()>2*window)flush(window);
 }flush(0);out.close();ofstream report(argv[3]);report<<"{\"lines_before\":"<<before<<",\"lines_after\":"<<after<<",\"removed\":{";bool first=true;uint64_t nonlinear=0;for(auto [op,n]:removed){if(!first)report<<',';first=false;report<<'"'<<op<<"\":"<<n;if(op=="CCX"||op=="CCZ"||op=="CSWAP")nonlinear+=n;}report<<"},\"nonlinear_instructions_removed\":"<<nonlinear<<",\"window\":"<<window<<"}\n";cout<<"K099_CANCEL before="<<before<<" after="<<after<<" nonlinear_removed="<<nonlinear<<'\n';}
