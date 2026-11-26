// Lời giải mẫu: một socket UDP, mỗi recvfrom là đúng một lệnh; trạng thái dùng chung trong bộ nhớ.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_FLIGHTS 1000
#define MAXLEN 1000
#define MAXTOK 8

typedef struct {
    char code[16], date[16];
    int state;  // 0 = ON_TIME, 1 = DELAYED, 2 = CANCELLED
    int minutes;
} Entry;

static Entry tab[MAX_FLIGHTS];
static int ntab = 0;

static void load_flights(void) {
    FILE *f = fopen("flights.txt", "r");
    if (!f) { perror("flights.txt"); exit(1); }
    char line[512], code[16], air[8], from[8], to[8], date[16];
    while (ntab < MAX_FLIGHTS && fgets(line, sizeof line, f)) {
        if (sscanf(line, "%15s %7s %7s %7s %15s", code, air, from, to, date) == 5) {
            strcpy(tab[ntab].code, code);
            strcpy(tab[ntab].date, date);
            ntab++;
        }
    }
    fclose(f);
}

static Entry *find(const char *code, const char *date) {
    for (int i = 0; i < ntab; i++)
        if (strcmp(tab[i].code, code) == 0 && strcmp(tab[i].date, date) == 0) return &tab[i];
    return NULL;
}

// minutes: 1..1440, không dấu, không số 0 đứng đầu.
static int parse_minutes(const char *s) {
    size_t n = strlen(s);
    if (n < 1 || n > 4 || s[0] == '0') return -1;
    int v = 0;
    for (size_t i = 0; i < n; i++) {
        if (s[i] < '0' || s[i] > '9') return -1;
        v = v * 10 + (s[i] - '0');
    }
    return v >= 1 && v <= 1440 ? v : -1;
}

static void build_reply(char *msg, const char *key, char *out, size_t cap) {
    char *tok[MAXTOK + 1];
    int nt = 0;
    for (char *p = msg;;) {
        if (nt < MAXTOK) tok[nt] = p;
        nt++;
        char *sp = strchr(p, ' ');
        if (!sp) break;
        *sp = 0;
        p = sp + 1;
    }
    if (nt > MAXTOK) { snprintf(out, cap, "ERROR\n"); return; }

    if (strcmp(tok[0], "STATUS") == 0 && nt == 3) {
        Entry *e = find(tok[1], tok[2]);
        if (!e) snprintf(out, cap, "NOT_FOUND\n");
        else if (e->state == 0) snprintf(out, cap, "ON_TIME\n");
        else if (e->state == 1) snprintf(out, cap, "DELAYED %d\n", e->minutes);
        else snprintf(out, cap, "CANCELLED\n");
        return;
    }
    if (strcmp(tok[0], "SET") == 0 && (nt == 5 || nt == 6)) {
        int state = -1, minutes = 0;
        if (nt == 5 && strcmp(tok[4], "ON_TIME") == 0) state = 0;
        else if (nt == 5 && strcmp(tok[4], "CANCELLED") == 0) state = 2;
        else if (nt == 6 && strcmp(tok[4], "DELAYED") == 0 && (minutes = parse_minutes(tok[5])) > 0) state = 1;
        if (state < 0) { snprintf(out, cap, "ERROR\n"); return; }
        if (strcmp(tok[1], key) != 0) { snprintf(out, cap, "DENIED\n"); return; }
        Entry *e = find(tok[2], tok[3]);
        if (!e) { snprintf(out, cap, "NOT_FOUND\n"); return; }
        e->state = state;
        e->minutes = minutes;
        snprintf(out, cap, "OK\n");
        return;
    }
    snprintf(out, cap, "ERROR\n");
}

int main(int argc, char *argv[]) {
    if (argc != 3) { fprintf(stderr, "usage: %s <port> <key>\n", argv[0]); return 1; }
    load_flights();
    int s = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(s, (struct sockaddr *)&addr, sizeof addr) < 0) { perror("bind"); return 1; }

    static char buf[2048];
    for (;;) {
        struct sockaddr_in from;
        socklen_t flen = sizeof from;
        ssize_t n = recvfrom(s, buf, sizeof buf - 1, 0, (struct sockaddr *)&from, &flen);
        if (n < 0) continue;
        char out[64];
        if (n > MAXLEN) {
            snprintf(out, sizeof out, "ERROR\n");
        } else {
            buf[n] = 0;
            if (n && buf[n - 1] == '\n') buf[--n] = 0;
            if (n && buf[n - 1] == '\r') buf[--n] = 0;
            build_reply(buf, argv[2], out, sizeof out);
        }
        sendto(s, out, strlen(out), 0, (struct sockaddr *)&from, flen);
    }
}
