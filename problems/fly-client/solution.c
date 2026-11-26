// Lời giải mẫu: select() trên stdin và socket; stdin đọc bằng read(0) + tự tách dòng (không dùng fgets để khỏi lệch với select).
#include <arpa/inet.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

static int sock;
static char rb[16384], ib[4096];
static size_t rlen, ilen;
static int stdin_eof;

static void send_line(const char *fmt, ...) {
    char buf[1024];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(buf, sizeof buf - 1, fmt, ap);
    va_end(ap);
    buf[n++] = '\n';
    send(sock, buf, (size_t)n, 0);
}

static void quit_ok(void) {
    send_line("QUIT");
    close(sock);
    exit(0);
}

// Lấy một dòng đầy đủ khỏi bộ đệm (bỏ '\n' và '\r'); trả về 0 nếu chưa đủ dòng.
static int take_line(char *buf, size_t *len, char *out, size_t cap) {
    char *nl = memchr(buf, '\n', *len);
    if (!nl) return 0;
    size_t n = (size_t)(nl - buf);
    size_t copy = n < cap - 1 ? n : cap - 1;
    memcpy(out, buf, copy);
    out[copy] = 0;
    if (copy && out[copy - 1] == '\r') out[copy - 1] = 0;
    memmove(buf, nl + 1, *len - n - 1);
    *len -= n + 1;
    return 1;
}

static void server_gone(void) {
    printf("Mat ket noi\n");
    fflush(stdout);
    exit(1);
}

// Đọc thêm từ socket vào rb; server đóng thì thoát.
static void pump_socket(void) {
    ssize_t n = recv(sock, rb + rlen, sizeof rb - rlen, 0);
    if (n <= 0) server_gone();
    rlen += (size_t)n;
}

static int is_notify(const char *line) { return strncmp(line, "301 NOTIFY ", 11) == 0; }

static void show_notify(const char *line) {
    printf("[THONG BAO] %s\n", line + 11);
    fflush(stdout);
}

// Chờ một dòng phản hồi (bỏ qua và in các thông báo xen giữa).
static void response_line(char *out, size_t cap) {
    for (;;) {
        while (!take_line(rb, &rlen, out, cap)) {
            fd_set rd;
            FD_ZERO(&rd);
            FD_SET(sock, &rd);
            select(sock + 1, &rd, NULL, NULL, NULL);
            pump_socket();
        }
        if (!is_notify(out)) return;
        show_notify(out);
    }
}

// Chờ người dùng gõ một dòng, trong lúc đó in ngay mọi thông báo từ server. Trả về 0 nếu stdin EOF.
static int user_line(char *out, size_t cap) {
    for (;;) {
        char line[1024];
        while (take_line(rb, &rlen, line, sizeof line))
            if (is_notify(line)) show_notify(line);
        if (take_line(ib, &ilen, out, cap)) return 1;
        if (stdin_eof) {
            if (!ilen) return 0;
            size_t n = ilen < cap - 1 ? ilen : cap - 1;
            memcpy(out, ib, n);
            out[n] = 0;
            ilen = 0;
            return 1;
        }
        fflush(stdout);
        fd_set rd;
        FD_ZERO(&rd);
        FD_SET(STDIN_FILENO, &rd);
        FD_SET(sock, &rd);
        if (select(sock + 1, &rd, NULL, NULL, NULL) < 0) continue;
        if (FD_ISSET(sock, &rd)) pump_socket();
        if (FD_ISSET(STDIN_FILENO, &rd)) {
            ssize_t n = read(STDIN_FILENO, ib + ilen, sizeof ib - ilen);
            if (n <= 0) stdin_eof = 1;
            else ilen += (size_t)n;
        }
    }
}

static void ask(const char *label, char *out, size_t cap) {
    printf("%s", label);
    fflush(stdout);
    if (!user_line(out, cap)) quit_ok();
}

static void print_menu(void) {
    printf("=== FLY ===\n1. Dang nhap\n2. Tim chuyen\n3. Dat ve\n4. Ve cua toi\n5. Thoat\nChon: ");
    fflush(stdout);
}

static void error_line(const char *line) {
    printf("Loi: %s\n", line);
    fflush(stdout);
}

int main(int argc, char *argv[]) {
    if (argc != 3) { fprintf(stderr, "Usage: %s <ip> <port>\n", argv[0]); return 1; }
    sock = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = inet_addr(argv[1]);
    a.sin_port = htons(atoi(argv[2]));
    if (a.sin_addr.s_addr == INADDR_NONE || connect(sock, (struct sockaddr *)&a, sizeof a) < 0) {
        printf("Khong ket noi duoc\n");
        return 1;
    }
    char line[1024], f[6][256];
    response_line(line, sizeof line);
    if (strncmp(line, "500", 3) == 0) {
        printf("Server day: %s\n", line);
        return 1;
    }

    for (;;) {
        print_menu();
        if (!user_line(line, sizeof line)) quit_ok();
        if (!strcmp(line, "1")) {
            ask("User: ", f[0], sizeof f[0]);
            ask("Pass: ", f[1], sizeof f[1]);
            send_line("LOGIN %s %s", f[0], f[1]);
            response_line(line, sizeof line);
            if (!strncmp(line, "100 OK ", 7)) printf("Xin chao %s\n", line + 7);
            else error_line(line);
        } else if (!strcmp(line, "2")) {
            ask("Di: ", f[0], sizeof f[0]);
            ask("Den: ", f[1], sizeof f[1]);
            ask("Ngay: ", f[2], sizeof f[2]);
            ask("So khach: ", f[3], sizeof f[3]);
            ask("Hang (ECO/BUS): ", f[4], sizeof f[4]);
            send_line("SEARCH %s %s %s %s %s", f[0], f[1], f[2], f[3], f[4]);
            response_line(line, sizeof line);
            int k;
            if (sscanf(line, "110 FLIGHTS %d", &k) == 1) {
                printf("Co %d chuyen:\n", k);
                for (int i = 1; i <= k; i++) {
                    char code[64], air[16], dep[16], arr[16], total[32];
                    response_line(line, sizeof line);
                    if (sscanf(line, "%63s %15s %15s %15s %31s", code, air, dep, arr, total) == 5)
                        printf("%d. %s %s %s-%s %s\n", i, code, air, dep, arr, total);
                }
            } else {
                error_line(line);
            }
        } else if (!strcmp(line, "3")) {
            ask("Chuyen: ", f[0], sizeof f[0]);
            ask("Ngay: ", f[1], sizeof f[1]);
            ask("Hang (ECO/BUS): ", f[2], sizeof f[2]);
            ask("So khach: ", f[3], sizeof f[3]);
            send_line("BOOK %s %s %s %s", f[0], f[1], f[2], f[3]);
            response_line(line, sizeof line);
            char pnr[64], amount[32], deadline[32];
            if (sscanf(line, "100 OK HOLD %63s %31s %31s", pnr, amount, deadline) == 3) {
                printf("Giu cho thanh cong. Ma: %s So tien: %s Han: %s\n", pnr, amount, deadline);
                ask("Thanh toan (1=Vi, 2=The, 0=Bo qua): ", f[4], sizeof f[4]);
                int pay = 0;
                if (!strcmp(f[4], "1")) {
                    send_line("PAY %s WALLET", pnr);
                    pay = 1;
                } else if (!strcmp(f[4], "2")) {
                    ask("So the: ", f[0], sizeof f[0]);
                    ask("Het han (MM/YY): ", f[1], sizeof f[1]);
                    ask("CVV: ", f[2], sizeof f[2]);
                    send_line("PAY %s CARD %s %s %s", pnr, f[0], f[1], f[2]);
                    pay = 1;
                }
                if (pay) {
                    response_line(line, sizeof line);
                    if (!strncmp(line, "100 OK PAID ", 12)) printf("Da thanh toan %s\n", line + 12);
                    else error_line(line);
                } else {
                    printf("Chua thanh toan\n");
                }
            } else {
                error_line(line);
            }
        } else if (!strcmp(line, "4")) {
            send_line("MYTICKETS");
            response_line(line, sizeof line);
            int k;
            if (sscanf(line, "110 TICKETS %d", &k) == 1) {
                printf("Ban co %d ve:\n", k);
                for (int i = 1; i <= k; i++) {
                    char no[64], fl[32], date[32], cls[16], pax[64], price[32], st[32];
                    response_line(line, sizeof line);
                    if (sscanf(line, "%63s %31s %31s %15s %63s %31s %31s", no, fl, date, cls, pax, price, st) == 7)
                        printf("%d. %s %s %s %s %s\n", i, no, fl, date, cls, st);
                }
            } else {
                error_line(line);
            }
        } else if (!strcmp(line, "5")) {
            send_line("QUIT");
            response_line(line, sizeof line);
            close(sock);
            return 0;
        } else {
            printf("Lua chon khong hop le\n");
        }
        fflush(stdout);
    }
}
