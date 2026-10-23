# Concise compiler vectorization summary

The rows show compiler-reported vectorization of function loops. For runtime-variable stride, the compiler may create a vectorized unit-stride branch and a scalar nonunit-stride branch; this table alone does not prove every stride used packed SIMD.

| Build | Kernel | Source line | Vector widths reported | Interpretation |
|---|---|---:|---|---|
| `float32_default` | saxpy_kernel | 77 | 16, 8 | Reported optimized branch |
| `float32_default` | multiply_kernel | 83 | 16, 8 | Reported optimized branch |
| `float32_default` | dot_kernel | 90 | 16 | Reported optimized branch |
| `float32_native` | saxpy_kernel | 77 | 16, 32 | Reported optimized branch |
| `float32_native` | multiply_kernel | 83 | 16, 32 | Reported optimized branch |
| `float32_native` | dot_kernel | 90 | 16, 32 | Reported optimized branch |
| `float32_scalar` | saxpy_kernel | 77 | — | Vectorization disabled by scalar flags |
| `float32_scalar` | multiply_kernel | 83 | — | Vectorization disabled by scalar flags |
| `float32_scalar` | dot_kernel | 90 | — | Vectorization disabled by scalar flags |
| `float64_default` | saxpy_kernel | 77 | 16 | Reported optimized branch |
| `float64_default` | multiply_kernel | 83 | 16 | Reported optimized branch |
| `float64_default` | dot_kernel | 90 | 16 | Reported optimized branch |
| `float64_native` | saxpy_kernel | 77 | 16, 32 | Reported optimized branch |
| `float64_native` | multiply_kernel | 83 | 16, 32 | Reported optimized branch |
| `float64_native` | dot_kernel | 90 | 16, 32 | Reported optimized branch |
| `float64_scalar` | saxpy_kernel | 77 | — | Vectorization disabled by scalar flags |
| `float64_scalar` | multiply_kernel | 83 | — | Vectorization disabled by scalar flags |
| `float64_scalar` | dot_kernel | 90 | — | Vectorization disabled by scalar flags |

To support your actual runtime claims, retain the full report files in the repository, select short relevant excerpts in the report, and avoid presenting a vectorized loop version as proof that a particular stride took that branch.
