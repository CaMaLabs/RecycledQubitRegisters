// Host validation bridge for an external CADO GPU header; no CUDA execution.
#include <iostream>
#include "gpu_ecm_mp.cuh"

template<int K> void check_row() {
    u64 n[K],a[K],b[K],r[K],alias[K],sum[K],diff[K],np;
    std::cin >> std::hex >> np;
    for (auto &v:n) std::cin >> v;
    for (auto &v:a) std::cin >> v;
    for (auto &v:b) std::cin >> v;
    if (!std::cin) throw "truncated input";
    montmul<K>(r,a,b,n,np);
    mp_copy<K>(alias,a);
    montmul<K>(alias,alias,b,n,np);
    addmod<K>(sum,a,b,n);
    submod<K>(diff,a,b,n);
    for (auto array:{r,alias,sum,diff})
        for (int i=0;i<K;i++) std::cout << std::hex << array[i] << ' ';
    std::cout << '\n';
}

int main() {
    int k;
    while (std::cin >> std::dec >> k) {
        switch (k) {
            case 2: check_row<2>(); break;
            case 4: check_row<4>(); break;
            case 8: check_row<8>(); break;
            case 16: check_row<16>(); break;
            case 33: check_row<33>(); break;
            default: return 2;
        }
    }
}
