// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, unistd, pthread, arpa/inet, sys/socket)

void *greet(void *arg) {
    // TODO: lấy fd từ arg, free(arg), sleep(1), send "Hello!\n" (7 byte), close(fd), return NULL
    return NULL;
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen(.., 64)
    // TODO: vòng lặp accept -> malloc một int chứa fd -> pthread_create(..., greet, p) -> pthread_detach
    return 0;
}
