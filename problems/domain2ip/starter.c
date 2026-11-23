// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, netdb, stdio, string)

int main(void) {
    char name[512];
    while (fgets(name, sizeof name, stdin)) {
        name[strcspn(name, "\r\n")] = 0;
        if (!name[0]) continue;
        // TODO: getaddrinfo với hints AF_INET + SOCK_STREAM, in "<tên>: ip1 ip2 ..." hoặc NOT_FOUND
    }
    return 0;
}
