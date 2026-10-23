# Baseline comparisons for the final report (float32)

Median of raw trial times. Speedup >1 means faster than scalar.

| Kernel | N | scalar_ms | default_ms | native_ms | default_speedup | native_speedup | native_GFLOP_s | native_cycles_per_element |
|---|---|---|---|---|---|---|---|---|
| SAXPY | 16384 | 0.00547 | 0.00142 | 0.00111 | 3.863 | 4.929 | 29.503 | 0.169 |
| SAXPY | 1048576 | 0.34695 | 0.1871 | 0.1689 | 1.854 | 2.054 | 12.417 | 0.403 |
| SAXPY | 16777216 | 7.0322 | 5.7502 | 5.4482 | 1.223 | 1.291 | 6.159 | 0.788 |
| Multiply | 16384 | 0.00463 | 0.00192 | 0.00133 | 2.412 | 3.472 | 12.282 | 0.202 |
| Multiply | 1048576 | 0.33045 | 0.274 | 0.24615 | 1.206 | 1.342 | 4.26 | 0.576 |
| Multiply | 16777216 | 7.936 | 6.89455 | 7.14595 | 1.151 | 1.111 | 2.348 | 1.041 |
| DotProduct | 16384 | 0.00821 | 0.00833 | 0.0081 | 0.986 | 1.013 | 4.044 | 1.226 |
| DotProduct | 1048576 | 0.4626 | 0.51805 | 0.5288 | 0.893 | 0.875 | 3.966 | 1.242 |
| DotProduct | 16777216 | 8.0606 | 8.05485 | 8.05145 | 1.001 | 1.001 | 4.168 | 1.177 |

Supplementary measurements (including thread cycles per element when available) are in `report_numbers.csv`.
