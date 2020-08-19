#include <string>
#include <iostream>

void func1(int i);

void func2(int i);

void func1(int i) {
    if (i == 0)
        return;
    func2(i - 1);
}

void func2(int i) {
    if (i == 0)
        return;
    func1(i - 1);
}

int main(int argc, char **argv) {
    std::string hello = "Hello from C++";
    std::cout << hello << std::endl;
}
