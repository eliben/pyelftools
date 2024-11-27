#include <stdio.h>

int addNumbers(int a, int b) {
    return a + b;
}

int main() {
    int num1 = 7;
    int num2 = 3;
    int sum = addNumbers(num1, num2);

    printf("Sum of %d and %d is %d\n", num1, num2, sum);
    return 0;
}

