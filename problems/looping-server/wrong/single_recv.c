// SAI có chủ đích: giả định một lần recv nhận đủ cả yêu cầu HTTP (như html.c).
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

#define REQ_MAX 8192

// Như html.c: gửi header trước, rồi nội dung (socket blocking: send chờ tới khi gửi hết).
static void respond(int c, const char *status, const char *type, const char *body, size_t len) {
    char head[256];
    sprintf(head, "HTTP/1.1 %s\r\nContent-Type: %s\r\nContent-Length: %zu\r\nConnection: close\r\n\r\n",
            status, type, len);
    send(c, head, strlen(head), 0);
    if (len) send(c, body, len, 0);
}

static void error(int c, const char *status) {
    char body[64];
    snprintf(body, sizeof body, "%s\n", strchr(status, ' ') + 1);
    respond(c, status, "text/plain; charset=utf-8", body, strlen(body));
}

static const char *mime(const char *path) {
    const char *dot = strrchr(path, '.');
    if (dot && !strcmp(dot, ".html")) return "text/html; charset=utf-8";
    if (dot && !strcmp(dot, ".txt")) return "text/plain; charset=utf-8";
    if (dot && !strcmp(dot, ".png")) return "image/png";
    return "application/octet-stream";
}

static void serve(int c, const char *root) {
    char req[REQ_MAX + 1];
    ssize_t k = recv(c, req, REQ_MAX, 0);  // SAI: giả định một lần recv nhận đủ cả yêu cầu
    if (k <= 0) return;
    req[k] = 0;
    char method[16], path[REQ_MAX + 1], version[32], extra;
    char *eol = strstr(req, "\r\n");
    if (eol) *eol = 0;
    if (sscanf(req, "%15s %8192s %31s %c", method, path, version, &extra) != 3) return error(c, "400 Bad Request");
    if (strcmp(method, "GET")) return error(c, "405 Method Not Allowed");
    path[strcspn(path, "?")] = 0;
    if (strstr(path, "..")) return error(c, "403 Forbidden");

    char file[2048];
    snprintf(file, sizeof file, "%s%s%s", root, path, path[strlen(path) - 1] == '/' ? "index.html" : "");
    struct stat st;
    FILE *f;
    if (stat(file, &st) < 0 || !S_ISREG(st.st_mode) || !(f = fopen(file, "rb"))) return error(c, "404 Not Found");
    char *body = malloc((size_t)st.st_size + 1);
    size_t n = fread(body, 1, (size_t)st.st_size, f);
    fclose(f);
    respond(c, "200 OK", mime(file), body, n);
    free(body);
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <port> <root_dir>\n", argv[0]);
        return 1;
    }
    int ls = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(ls, (struct sockaddr *)&addr, sizeof addr) < 0 || listen(ls, 16) < 0) {
        perror("bind/listen");
        return 1;
    }
    for (;;) {
        int c = accept(ls, NULL, NULL);
        if (c < 0) continue;
        serve(c, argv[2]);
        close(c);
    }
}
