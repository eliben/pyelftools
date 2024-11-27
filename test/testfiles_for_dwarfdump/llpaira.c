#include <stdio.h>
void a(int n)
{
    int i;
    for(i=0;i<n;i++)
        printf("%d\n", i*i);
    for(i=0;i<10;i++)
        printf("%d\n", i*i+76543*i);
    printf("%d\n", n);
}