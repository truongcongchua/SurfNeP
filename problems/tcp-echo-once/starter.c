// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, string, unistd, arpa/inet, sys/socket)

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen -> accept một client (như bài tcp-accept-close)
    // TODO: char buffer[1024]; bytes_received = recv(client, buffer, sizeof(buffer), 0);  (-1: perror + exit)
    // TODO: send(client, buffer, bytes_received, 0);   // đúng số byte nhận được
    // TODO: close(client); close(listener); return 0;
    return 0;
}
