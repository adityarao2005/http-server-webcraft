#include <iostream>
#include <atomic>
#include <webcraft/async/async.hpp>
#include <csignal>
#include <sstream>

using namespace webcraft::async;
using namespace webcraft::async::io::socket;

std::atomic<bool> shutdown_requested{false};

connection_info conn{
    .host = "0.0.0.0",
    .port = 8080};

void signal_handler(int signal)
{
    if (signal == SIGINT)
    {
        std::cout << "\nShutdown requested..." << std::endl;
        shutdown_requested.store(true);

        auto close_fn = co_async
        {
            tcp_socket dummy_socket = make_tcp_socket();
            co_await dummy_socket.connect(conn);
            co_await dummy_socket.close();
            std::cout << "Dummy connection closed to unblock accept()" << std::endl;
        };

        sync_wait(close_fn());
    }
}

async_t(void) handle_client(tcp_socket socket)
{
    auto &reader = socket.get_readable_stream();
    auto &writer = socket.get_writable_stream();

    char buffer[4096];

    try
    {
        // Read the HTTP request
        std::size_t n = co_await reader.recv(std::span<char>(buffer, sizeof(buffer)));
        if (n == 0)
        {
            co_await socket.close();
            co_return;
        }

        // Parse the request line (METHOD PATH HTTP/VERSION)
        std::string request(buffer, n);
        std::istringstream request_stream(request);
        std::string method, path, version;
        request_stream >> method >> path >> version;

        std::cout << "Request: " << method << " " << path << " " << version << std::endl;

        // Read headers (simple parsing)
        std::string line;
        while (std::getline(request_stream, line) && line != "\r")
        {
            if (!line.empty())
            {
                std::cout << "Header: " << line << std::endl;
            }
        }

        // Create HTTP response
        std::string response_body = R"(<!DOCTYPE html>
<html>
<head>
    <title>Hello World</title>
</head>
<body>
    <h1>Hello World!</h1>
    <p>Method: )" + method + R"(</p>
    <p>Path: )" + path + R"(</p>
</body>
</html>)";

        std::string response = "HTTP/1.1 200 OK\r\n"
                               "Content-Type: text/html\r\n"
                               "Content-Length: " +
                               std::to_string(response_body.size()) + "\r\n"
                                                                      "Connection: close\r\n"
                                                                      "\r\n" +
                               response_body;

        // Send response
        co_await writer.send(std::span<char>(response.data(), response.size()));
    }
    catch (const std::exception &e)
    {
        std::cerr << "Client handling error: " << e.what() << std::endl;
    }

    co_await socket.close();
}

int main()
{
    // Register signal handler
    std::signal(SIGINT, signal_handler);

    runtime_context ctx;

    auto server_fn = co_async
    {
        std::cout << "Starting HTTP server on " << conn.host << ":" << conn.port << "..." << std::endl;

        tcp_listener listener = make_tcp_listener();
        listener.bind(conn);
        listener.listen(0);

        std::cout << "Waiting for incoming connections..." << std::endl;

        while (!shutdown_requested.load())
        {
            std::cout << "Accepting incoming connections..." << std::endl;

            auto peer = co_await listener.accept();

            std::cout << "Accepted connection from " << peer.get_remote_host() << ":" << peer.get_remote_port() << std::endl;

            co_await handle_client(std::move(peer));

            std::cout << "Connection handled and closed." << std::endl;
        }

        std::cout << "HTTP server shut down" << std::endl;
    };

    sync_wait(server_fn());

    webcraft::async::detail::shutdown_runtime();

    std::cout << "Server exited cleanly." << std::endl;

    return 0;
}