// SAI có chủ đích: pthread_join ngay sau khi tạo -> thực chất vẫn phục vụ tuần tự -> BLOCKED.
#include <arpa/inet.h>
#include <pthread.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>

static void *worker(void *arg) {
    int c = (int)(intptr_t)arg;
    char buf[8192];
    ssize_t k;
    while ((k = recv(c, buf, sizeof buf, 0)) > 0) send(c, buf, (size_t)k, MSG_NOSIGNAL);
    close(c);
    return NULL;
}

int main(int argc, char *argv[]) {
    (void)argc;
    int ls = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_port = htons(atoi(argv[1]));
    bind(ls, (struct sockaddr *)&a, sizeof a);
    listen(ls, 64);
    for (;;) {
        int c = accept(ls, NULL, NULL);
        pthread_t t;
        pthread_create(&t, NULL, worker, (void *)(intptr_t)c);
        pthread_join(t, NULL);
    }
}
