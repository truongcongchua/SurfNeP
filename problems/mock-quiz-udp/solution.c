// Lời giải mẫu: một socket UDP, bảng người chơi theo (IP, cổng).
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_Q 100
#define MAX_PLAYERS 100

typedef struct {
    int used;
    struct sockaddr_in addr;
    char name[33];
    int correct, answered;
    char done[MAX_Q + 1];
} Player;

static char qtext[MAX_Q][512];  // dòng câu hỏi đã bỏ "|<đáp án>"
static char qans[MAX_Q];
static int nq;
static Player pl[MAX_PLAYERS];
static int limit;

static void load(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) {
        perror(path);
        exit(1);
    }
    char line[600];
    while (nq < MAX_Q && fgets(line, sizeof line, f)) {
        line[strcspn(line, "\r\n")] = 0;
        char *bar = strrchr(line, '|');
        if (!line[0] || !bar) continue;
        qans[nq] = bar[1];
        *bar = 0;
        snprintf(qtext[nq], sizeof qtext[nq], "%s", line);
        nq++;
    }
    fclose(f);
}

static Player *find(const struct sockaddr_in *a) {
    for (int i = 0; i < MAX_PLAYERS; i++)
        if (pl[i].used && pl[i].addr.sin_addr.s_addr == a->sin_addr.s_addr && pl[i].addr.sin_port == a->sin_port)
            return &pl[i];
    return NULL;
}

static int count_players(void) {
    int n = 0;
    for (int i = 0; i < MAX_PLAYERS; i++) n += pl[i].used;
    return n;
}

static int parse_index(const char *s) {
    if (!*s || strlen(s) > 3) return 0;
    for (const char *p = s; *p; p++)
        if (*p < '0' || *p > '9') return 0;
    int i = atoi(s);
    return i >= 1 && i <= nq ? i : 0;
}

// a xếp trước b? Nhiều câu đúng hơn trước; bằng nhau thì tên nhỏ hơn (strcmp) trước.
static int ranks_before(const Player *a, const Player *b) {
    if (a->correct != b->correct) return a->correct > b->correct;
    return strcmp(a->name, b->name) < 0;
}

static void handle(char *req, const struct sockaddr_in *from, char *out, size_t cap) {
    char *tok[4], *save = NULL;
    int nt = 0;
    for (char *t = strtok_r(req, " ", &save); t && nt < 4; t = strtok_r(NULL, " ", &save)) tok[nt++] = t;
    const char *cmd = nt ? tok[0] : "";
    Player *p = find(from);

    if (!strcmp(cmd, "JOIN") && nt == 2 && strlen(tok[1]) <= 32) {
        if (p) snprintf(out, cap, "ALREADY");
        else if (count_players() >= limit) snprintf(out, cap, "FULL");
        else {
            for (int i = 0; i < MAX_PLAYERS; i++)
                if (!pl[i].used) {
                    memset(&pl[i], 0, sizeof pl[i]);
                    pl[i].used = 1;
                    pl[i].addr = *from;
                    strcpy(pl[i].name, tok[1]);
                    break;
                }
            snprintf(out, cap, "WELCOME %s %d", tok[1], nq);
        }
        return;
    }
    int known = (!strcmp(cmd, "Q") && nt == 2) || (!strcmp(cmd, "ANS") && nt == 3) ||
                ((!strcmp(cmd, "SCORE") || !strcmp(cmd, "TOP") || !strcmp(cmd, "LEAVE")) && nt == 1);
    if (!known) {
        snprintf(out, cap, "ERROR");
        return;
    }
    if (!p) {
        snprintf(out, cap, "JOIN_FIRST");
        return;
    }
    if (!strcmp(cmd, "Q")) {
        int i = parse_index(tok[1]);
        if (!i) snprintf(out, cap, "INVALID");
        else snprintf(out, cap, "Q %d %s", i, qtext[i - 1]);
    } else if (!strcmp(cmd, "ANS")) {
        int i = parse_index(tok[1]);
        char x = tok[2][0];
        if (!i || strlen(tok[2]) != 1 || x < 'A' || x > 'D') snprintf(out, cap, "INVALID");
        else if (p->done[i]) snprintf(out, cap, "ANSWERED");
        else {
            p->done[i] = 1;
            p->answered++;
            int ok = x == qans[i - 1];
            p->correct += ok;
            snprintf(out, cap, ok ? "CORRECT" : "WRONG");
        }
    } else if (!strcmp(cmd, "SCORE")) {
        snprintf(out, cap, "SCORE %d %d", p->correct, p->answered);
    } else if (!strcmp(cmd, "TOP")) {
        Player *rank[MAX_PLAYERS];
        int n = 0;
        for (int i = 0; i < MAX_PLAYERS; i++)
            if (pl[i].used) rank[n++] = &pl[i];
        for (int i = 0; i < n; i++)  // sắp xếp chọn
            for (int j = i + 1; j < n; j++)
                if (ranks_before(rank[j], rank[i])) {
                    Player *t = rank[i];
                    rank[i] = rank[j];
                    rank[j] = t;
                }
        size_t len = (size_t)snprintf(out, cap, "TOP");
        for (int i = 0; i < n && i < 3; i++)
            len += (size_t)snprintf(out + len, cap - len, " %s:%d", rank[i]->name, rank[i]->correct);
    } else {  // LEAVE
        p->used = 0;
        snprintf(out, cap, "BYE");
    }
}

int main(int argc, char *argv[]) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s <port> <questions_file> <N>\n", argv[0]);
        return 1;
    }
    load(argv[2]);
    limit = atoi(argv[3]);
    int s = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(s, (struct sockaddr *)&addr, sizeof addr) < 0) {
        perror("bind");
        return 1;
    }
    char req[1024], out[1024];
    for (;;) {
        struct sockaddr_in from;
        socklen_t fl = sizeof from;
        ssize_t n = recvfrom(s, req, sizeof req - 1, 0, (struct sockaddr *)&from, &fl);
        if (n < 0) continue;
        req[n] = 0;
        handle(req, &from, out, sizeof out);
        sendto(s, out, strlen(out), 0, (struct sockaddr *)&from, fl);
    }
}
