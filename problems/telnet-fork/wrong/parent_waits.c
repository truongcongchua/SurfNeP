// SAI có chủ đích: cha wait() con ngay sau fork -> chỉ phục vụ được một client mỗi lúc.
#include <arpa/inet.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>

#define BUF_SIZE 4096

// Như forking_server.c: thu dọn MỌI tiến trình con đã kết thúc.
void signal_handler(int signum) {
    while (waitpid(-1, NULL, WNOHANG) > 0);
}

static void send_str(int fd, const char *s) { send(fd, s, strlen(s), 0); }

// "user pass" (đúng một dấu cách) có trong accounts.txt?
static int check_login(const char *line) {
    const char *sp = strchr(line, ' ');
    if (!sp || sp == line || !sp[1] || strchr(sp + 1, ' ')) return 0;
    FILE *f = fopen("accounts.txt", "r");
    if (!f) return 0;
    char row[256];
    int ok = 0;
    while (!ok && fgets(row, sizeof row, f)) {
        row[strcspn(row, "\r\n")] = 0;
        ok = strcmp(row, line) == 0;
    }
    fclose(f);
    return ok;
}

static void run_command(int c, const char *cmd) {
    char out[64], shell[BUF_SIZE + 128];
    snprintf(out, sizeof out, "out_%d.txt", (int)getpid());
    if (!*cmd) {  // dòng rỗng: không có gì để chạy
        send_str(c, "OUTPUT 0\n");
        return;
    }
    // Bọc cả dòng trong { ...; } để gom kết quả của MỌI lệnh trên dòng (echo a; echo b, a | b...).
    snprintf(shell, sizeof shell, "{ %s\n} > %s 2>&1", cmd, out);
    system(shell);
    FILE *f = fopen(out, "rb");
    char *data = NULL;
    size_t len = 0;
    if (f) {
        fseek(f, 0, SEEK_END);
        len = (size_t)ftell(f);
        rewind(f);
        data = malloc(len + 1);
        len = fread(data, 1, len, f);
        fclose(f);
    }
    remove(out);
    char head[64];
    snprintf(head, sizeof head, "OUTPUT %zu\n", len);
    send_str(c, head);
    if (len) send(c, data, len, 0);  // socket blocking: send chờ tới khi gửi hết
    free(data);
}

static void session(int c) {
    char buf[BUF_SIZE];
    size_t len = 0;
    int logged = 0;
    for (;;) {
        ssize_t k = recv(c, buf + len, BUF_SIZE - 1 - len, 0);
        if (k <= 0) return;
        len += (size_t)k;
        buf[len] = 0;
        char *start = buf, *nl;
        while ((nl = strchr(start, '\n'))) {
            *nl = 0;
            if (nl > start && nl[-1] == '\r') nl[-1] = 0;
            if (!logged) {
                logged = check_login(start);
                send_str(c, logged ? "LOGIN OK\n" : "LOGIN FAIL\n");
            } else if (!strcmp(start, "exit")) {
                send_str(c, "BYE\n");
                return;
            } else {
                run_command(c, start);
            }
            start = nl + 1;
        }
        len -= (size_t)(start - buf);
        memmove(buf, start, len);
        if (len == BUF_SIZE - 1) len = 0;  // dòng quá dài: bỏ
    }
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    signal(SIGCHLD, signal_handler);

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
        if (fork() == 0) {
            close(ls);
            session(c);
            close(c);
            _exit(0);
        }
        close(c);
        while (wait(NULL) > 0);
    }
}
