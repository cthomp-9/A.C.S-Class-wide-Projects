
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>

int main(int argc, char *argv[]) {
    if (argc < 3) {
        printf("Usage: memory_kernel <size_MB> <stride_bytes>\n");
        return 1;
    }

    size_t size = (size_t)atoll(argv[1]) * 1024 * 1024;
    size_t stride = (size_t)atoll(argv[2]);

    if (size == 0 || stride < sizeof(uint64_t) ||
        stride % sizeof(uint64_t) != 0) {
        printf("Invalid size or stride.\n");
        return 1;
    }

    uint64_t *data = malloc(size);

    if (data == NULL) {
        printf("Memory allocation failed.\n");
        return 1;
    }

    size_t count = size / sizeof(uint64_t);
    size_t step = stride / sizeof(uint64_t);

    for (size_t i = 0; i < count; i++) {
        data[i] = i;
    }

    volatile uint64_t sum = 0;

    clock_t start = clock();

    for (int repeat = 0; repeat < 10000; repeat++) {
        for (size_t i = 0; i < count; i += step) {
            sum += data[i];
        }
    }

    clock_t end = clock();

    double elapsed = (double)(end - start) / CLOCKS_PER_SEC;

    printf("Size: %.2f MiB\n", (double)size / (1024 * 1024));
    printf("Stride: %zu bytes\n", stride);
    printf("Time: %.6f seconds\n", elapsed);
    printf("Checksum: %llu\n", (unsigned long long)sum);

    free(data);
    return 0;
}
