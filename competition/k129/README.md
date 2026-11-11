# K129: condition-XOR fusion

Hypothesis: two identical CCX, CCZ, or CSWAP involutions guarded by different classical measurement bits can become one involution guarded by their XOR, when intervening quantum operations are disjoint and neither guard changes. This saves two executed gates on shots where both guards are true.

The conservative source scan found no eligible pair among 7 Toffoli-class operations with one inline bit condition. The result does not cover every nested condition-stack pattern. No circuit candidate or verifier run was produced.
