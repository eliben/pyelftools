/* This code is in the public domain. */
#ifndef COMPUTE
#define COMPUTE compute64
#endif
#ifndef HELPER
#define HELPER helper64
#endif

__attribute__((noinline)) int HELPER(int input) {
    int result = input + 7;
    for (int i = 0; i < 3; i++) {
        result = result * 2 - i;
        __asm__ volatile ("" : "+r" (result));
    }
    return result;
}

__attribute__((noinline)) int COMPUTE(int input) {
    if (input < 0)
        return HELPER(-input);
    return HELPER(input) + 1;
}
