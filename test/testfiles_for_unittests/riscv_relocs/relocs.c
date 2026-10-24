/*
 * riscv64-linux-gnu-gcc -c -O2 -g -gdwarf-5 relocs.c -o relocs.o
 *
 * Built with GCC 14.2.0 and binutils 2.44 from Debian trixie.
 */

struct point { int x, y; };

static int counter;
int table[16];

static int scale(int a, struct point *p)
{
    counter += a;
    return p->x * a + p->y;
}

int sum(int n)
{
    int s = 0;
    for (int i = 0; i < n; i++)
        s += table[i & 15] * i;
    return s;
}

int combine(int a, int b, int c)
{
    struct point p = { a, b };
    return scale(c, &p) + sum(a);
}

extern void use(int *buf, int n);

int fill(int n)
{
    int buf[8];
    for (int i = 0; i < 8; i++)
        buf[i] = i * n + table[i & 15];
    use(buf, n);
    return buf[n & 7] + combine(n, buf[1], buf[2]);
}
