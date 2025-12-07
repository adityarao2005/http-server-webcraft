#include <iostream>
#include <atomic>
#include <webcraft/async/async.hpp>

int main()
{
    webcraft::async::runtime_context ctx;
    std::cout << "Hello, World!" << std::endl;
    return 0;
}