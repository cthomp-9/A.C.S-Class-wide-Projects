#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <time.h>
#endif
#if defined(__x86_64__) || defined(_M_X64)
#include <x86intrin.h>
#define HAS_TSC 1
#else
#define HAS_TSC 0
#endif

/* Build with -DDTYPE_DOUBLE=1 for float64; otherwise float32. */
#ifdef DTYPE_DOUBLE
typedef double value_t;
#define TYPE_NAME "float64"
#else
typedef float value_t;
#define TYPE_NAME "float32"
#endif

/* VS Code's MSVC IntelliSense parser doesn't understand GCC attributes. */
#if defined(__INTELLISENSE__)
#define NOIPA __declspec(noinline)
#elif defined(__GNUC__)
#define NOIPA __attribute__((noinline, noipa))
#else
#define NOIPA
#endif

#define TRIALS 9
#define ALIGNMENT 64U
#define TARGET_ELEMENTS 4000000U

volatile double checksum_sink = 0.0;

static double now_seconds(void) {
#ifdef _WIN32
    static LARGE_INTEGER frequency = {0};
    LARGE_INTEGER counter;
    if (frequency.QuadPart == 0) QueryPerformanceFrequency(&frequency);
    QueryPerformanceCounter(&counter);
    return (double)counter.QuadPart / (double)frequency.QuadPart;
#else
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec + (double)t.tv_nsec * 1e-9;
#endif
}

static unsigned long long read_ticks(void) {
#if HAS_TSC
    _mm_lfence();
    return (unsigned long long)__rdtsc();
#else
    return 0;
#endif
}

static unsigned long long thread_cycles(void) {
#ifdef _WIN32
    ULONG64 count = 0;
    if (QueryThreadCycleTime(GetCurrentThread(), &count))
        return (unsigned long long)count;
#endif
    return 0;
}

NOIPA void saxpy_kernel(const value_t *x, value_t *y,
                        value_t a, size_t n, size_t stride) {
    for (size_t i=0; i<n; ++i)
        y[i*stride] = a*x[i*stride] + y[i*stride];
}

NOIPA void multiply_kernel(const value_t *x, const value_t *y,
                           value_t *z, size_t n, size_t stride) {
    for (size_t i=0; i<n; ++i)
        z[i*stride] = x[i*stride] * y[i*stride];
}

NOIPA value_t dot_kernel(const value_t *x, const value_t *y,
                         size_t n, size_t stride) {
    value_t sum = (value_t)0;
    for (size_t i=0; i<n; ++i)
        sum += x[i*stride] * y[i*stride];
    return sum;
}

/* Allocate a 64-byte-aligned pointer that can optionally be shifted by one element. */
static value_t *allocate_values(size_t count, int shift, void **allocation) {
    size_t total = count*sizeof(value_t) + ALIGNMENT + sizeof(value_t);
    void *base = malloc(total);
    if (!base) return NULL;
    uintptr_t p = ((uintptr_t)base + ALIGNMENT-1) & ~((uintptr_t)ALIGNMENT-1);
    *allocation = base;
    return ((value_t *)p) + shift;
}

static int validate_outputs(int kernel, const value_t *x, const value_t *y,
                            const value_t *z, size_t n, size_t stride, value_t dot) {
    /* Exact values: x=1, y=2, z=2; in SAXPY, +1 then -1 resets y=2. */
    if (kernel == 2) {
        double expected = 2.0 * (double)n;
        double tolerance = 1e-5 * expected + 1e-6;
        return fabs((double)dot - expected) <= tolerance;
    }
    for (size_t i=0; i<n; ++i) {
        size_t pos=i*stride;
        if (x[pos] != (value_t)1 || y[pos] != (value_t)2) return 0;
        if (kernel == 1 && z[pos] != (value_t)2) return 0;
    }
    return 1;
}

static int run_case(FILE *out, const char *mode, const char *build,
                    const char *kernel_name, int kernel, size_t n,
                    size_t stride, int shift) {
    const size_t physical = (n-1)*stride + 1;
    void *bx=NULL,*by=NULL,*bz=NULL;
    value_t *x=allocate_values(physical,shift,&bx);
    value_t *y=allocate_values(physical,shift,&by);
    value_t *z=allocate_values(physical,shift,&bz);
    if (!x || !y || !z) {
        fprintf(stderr,"allocation failure for N=%zu stride=%zu\n",n,stride);
        free(bx); free(by); free(bz);
        return 0;
    }
    for (size_t i=0; i<physical; ++i) { x[i]=(value_t)1; y[i]=(value_t)2; z[i]=(value_t)0; }

    /* Two kernel calls per iteration-pair. SAXPY uses +a and -a, restoring y. */
    size_t pairs = TARGET_ELEMENTS/(2*n);
    if (pairs<1) pairs=1;
    if (pairs>10000) pairs=10000;

    /* Separate untimed correctness/warmup pass. */
    value_t sum=0;
    if (kernel==0) {
        saxpy_kernel(x,y,(value_t)1,n,stride);
        saxpy_kernel(x,y,(value_t)-1,n,stride);
    } else if (kernel==1) {
        multiply_kernel(x,y,z,n,stride);
    } else {
        sum=dot_kernel(x,y,n,stride);
    }
    if (!validate_outputs(kernel,x,y,z,n,stride,sum)) {
        fprintf(stderr,"FAIL (warmup): %s N=%zu stride=%zu offset=%d\n",kernel_name,n,stride,shift);
        free(bx);free(by);free(bz);return 0;
    }

    for (int trial=1; trial<=TRIALS; ++trial) {
        unsigned long long core0=thread_cycles();
        double start = now_seconds();
        unsigned long long c0=read_ticks();
        if (kernel==0) {
            for (size_t r=0;r<pairs;++r) {
                saxpy_kernel(x,y,(value_t)1,n,stride);
                saxpy_kernel(x,y,(value_t)-1,n,stride);
            }
        } else if (kernel==1) {
            for (size_t r=0;r<2*pairs;++r) multiply_kernel(x,y,z,n,stride);
        } else {
            for (size_t r=0;r<2*pairs;++r) {
                sum=dot_kernel(x,y,n,stride);
                checksum_sink=(double)sum;
            }
        }
        unsigned long long c1=read_ticks();
        double end=now_seconds();
        unsigned long long core1=thread_cycles();
        if (!validate_outputs(kernel,x,y,z,n,stride,sum)) {
            fprintf(stderr,"FAIL: %s N=%zu stride=%zu trial=%d\n",kernel_name,n,stride,trial);
            free(bx);free(by);free(bz);return 0;
        }
        /* Preserve visible results and raw trial times. */
        checksum_sink += kernel==2?(double)sum : (double)(kernel==0?y[(n-1)*stride]:z[(n-1)*stride]);
        double calls=(double)(2*pairs);
        double ms_per_call=(end-start)*1000.0/calls;
        double tsc_per_element=HAS_TSC?(double)(c1-c0)/(calls*(double)n):0.0;
        double cycles_per_element=(core1>core0)?(double)(core1-core0)/(calls*(double)n):0.0;
        fprintf(out,"%s,%s,%s,%s,%zu,%zu,%d,%zu,%d,%.9f,%.6f,%.6f,PASS\n",
                mode,build,TYPE_NAME,kernel_name,n,stride,shift*(int)sizeof(value_t),
                pairs,trial,ms_per_call,tsc_per_element,cycles_per_element);
    }
    printf("%s %s %-10s N=%-9zu stride=%zu offset=%d: PASS\n",
           build,TYPE_NAME,kernel_name,n,stride,shift*(int)sizeof(value_t));
    free(bx);free(by);free(bz);
    return 1;
}

int main(int argc, char **argv) {
    if (argc!=4) {
        fprintf(stderr,"Usage: %s baseline|alignment|stride scalar|default|native output.csv\n",argv[0]);
        return 2;
    }
    const char *mode=argv[1],*build=argv[2],*path=argv[3];
    if (strcmp(mode,"baseline") && strcmp(mode,"alignment") && strcmp(mode,"stride")) {
        fprintf(stderr,"Invalid mode: %s\n",mode);return 2;
    }
#ifdef _WIN32
    /* Fix the benchmark to logical CPU 0; core type must be verified separately. */
    if (!SetThreadAffinityMask(GetCurrentThread(), (DWORD_PTR)1)) {
        fprintf(stderr,"Warning: failed to pin to logical CPU 0\n");
    }
#endif
    FILE *out=fopen(path,"w");
    if (!out) { perror(path); return 1; }
    fprintf(out,"Mode,Build,Type,Kernel,N,Stride,Offset_bytes,Iteration_pairs,Trial,Time_ms,TSC_ticks_per_element,Thread_cycles_per_element,Correct\n");
    const char *names[]={"SAXPY","Multiply","DotProduct"};
    int ok=1;
    if (!strcmp(mode,"baseline")) {
        size_t sizes[]={256,1024,4096,16384,65536,262144,1048576,4194304,16777216};
        for (size_t j=0;j<sizeof(sizes)/sizeof(*sizes) && ok;++j)
            for (int k=0;k<3 && ok;++k)
                ok=run_case(out,mode,build,names[k],k,sizes[j],1,0);
    } else if (!strcmp(mode,"alignment")) {
        size_t sizes[]={16384,16387,1048576,1048579,4194304,4194307};
        for (size_t j=0;j<sizeof(sizes)/sizeof(*sizes) && ok;++j)
            for (int shift=0;shift<=1 && ok;++shift)
                for (int k=0;k<3 && ok;++k)
                    ok=run_case(out,mode,build,names[k],k,sizes[j],1,shift);
    } else {
        size_t sizes[]={16384,262144,1048576};
        size_t strides[]={1,2,4,8};
        for (size_t j=0;j<sizeof(sizes)/sizeof(*sizes) && ok;++j)
            for (size_t r=0;r<sizeof(strides)/sizeof(*strides) && ok;++r)
                for (int k=0;k<3 && ok;++k)
                    ok=run_case(out,mode,build,names[k],k,sizes[j],strides[r],0);
    }
    fclose(out);
    if (ok) printf("Saved %s (raw trials, all three kernels)\n",path);
    return ok?0:1;
}
