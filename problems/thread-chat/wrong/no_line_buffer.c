// SAI có chủ đích: không ghép dòng, coi mỗi recv() là một dòng.
#include <arpa/inet.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_CLIENTS 128
#define BUF_SIZE 4096

typedef struct { int fd; char id[64]; } Slot;  // fd = -1: ô trống; id rỗng: chưa đăng ký

static Slot slots[MAX_CLIENTS];
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;

static void send_str(int fd, const char *s) { send(fd, s, strlen(s), MSG_NOSIGNAL); }

static int valid_word(const char *s) { return *s && !strchr(s, ' '); }

static void broadcast(int from, const char *msg) {
    pthread_mutex_lock(&lock);
    for (int i = 0; i < MAX_CLIENTS; i++)
        if (i != from && slots[i].fd >= 0 && slots[i].id[0]) send_str(slots[i].fd, msg);
    pthread_mutex_unlock(&lock);
}

static void handle_line(int me, char *line) {
    size_t n = strlen(line);
    if (n && line[n - 1] == '\r') line[--n] = 0;
    int fd = slots[me].fd;
    if (!slots[me].id[0]) {
        char *sep = strstr(line, ": ");
        if (sep) {
            *sep = 0;
            if (valid_word(line) && valid_word(sep + 2) && strlen(line) < sizeof slots[me].id) {
                pthread_mutex_lock(&lock);
                strcpy(slots[me].id, line);
                pthread_mutex_unlock(&lock);
                char msg[96];
                snprintf(msg, sizeof msg, "OK %s\n", line);
                send_str(fd, msg);
                return;
            }
        }
        send_str(fd, "ERROR\n");
        return;
    }
    char msg[BUF_SIZE + 96];
    snprintf(msg, sizeof msg, "%s: %s\n", slots[me].id, line);
    broadcast(me, msg);
}

static void *worker(void *arg) {
    int me = (int)(intptr_t)arg;
    int fd = slots[me].fd;
    char buf[BUF_SIZE];
    for (;;) {
        ssize_t k = recv(fd, buf, BUF_SIZE - 1, 0);
        if (k <= 0) break;
        buf[k] = 0;
        buf[strcspn(buf, "\r\n")] = 0;  // SAI: mỗi recv = một dòng
        handle_line(me, buf);
    }
    pthread_mutex_lock(&lock);
    close(fd);
    slots[me].fd = -1;
    slots[me].id[0] = 0;
    pthread_mutex_unlock(&lock);
    return NULL;
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    for (int i = 0; i < MAX_CLIENTS; i++) slots[i].fd = -1;
    int ls = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(ls, (struct sockaddr *)&addr, sizeof addr) < 0 || listen(ls, 64) < 0) {
        perror("bind/listen");
        return 1;
    }
    for (;;) {
        int c = accept(ls, NULL, NULL);
        if (c < 0) continue;
        int me = -1;
        pthread_mutex_lock(&lock);
        for (int i = 0; i < MAX_CLIENTS && me < 0; i++)
            if (slots[i].fd < 0) me = i;
        if (me >= 0) {
            slots[me].fd = c;
            slots[me].id[0] = 0;
        }
        pthread_mutex_unlock(&lock);
        if (me < 0) {
            close(c);
            continue;
        }
        pthread_t t;
        if (pthread_create(&t, NULL, worker, (void *)(intptr_t)me) == 0) pthread_detach(t);
    }
}
