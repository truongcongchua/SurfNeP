// Lời giải mẫu: tách thủ công theo đúng một dấu cách, kiểm tra từng luật.
#include <stdio.h>
#include <string.h>

#define MAXTOK 32

static int is_upper(char c) { return c >= 'A' && c <= 'Z'; }
static int is_digit(char c) { return c >= '0' && c <= '9'; }

static int airport(const char *s) {
    return strlen(s) == 3 && is_upper(s[0]) && is_upper(s[1]) && is_upper(s[2]);
}

static int leap(int y) { return (y % 4 == 0 && y % 100 != 0) || y % 400 == 0; }

static int valid_date(const char *s) {
    if (strlen(s) != 10 || s[4] != '-' || s[7] != '-') return 0;
    for (int i = 0; i < 10; i++)
        if (i != 4 && i != 7 && !is_digit(s[i])) return 0;
    int y = (s[0] - '0') * 1000 + (s[1] - '0') * 100 + (s[2] - '0') * 10 + (s[3] - '0');
    int m = (s[5] - '0') * 10 + (s[6] - '0');
    int d = (s[8] - '0') * 10 + (s[9] - '0');
    static const int dim[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    if (y < 1900 || y > 2100 || m < 1 || m > 12 || d < 1) return 0;
    int max = dim[m - 1] + (m == 2 && leap(y));
    return d <= max;
}

static int valid_user(const char *s) {
    size_t n = strlen(s);
    if (n < 1 || n > 32) return 0;
    for (size_t i = 0; i < n; i++)
        if (!((s[i] >= 'a' && s[i] <= 'z') || is_digit(s[i]))) return 0;
    return 1;
}

static int valid_pass(const char *s) {
    size_t n = strlen(s);
    if (n < 4 || n > 32) return 0;
    for (size_t i = 0; i < n; i++)
        if ((unsigned char)s[i] < 0x21 || (unsigned char)s[i] > 0x7E) return 0;
    return 1;
}

static int valid_search(char **t, int nt) {
    if (nt != 6 && nt != 7) return 0;
    if (!airport(t[1]) || !airport(t[2]) || strcmp(t[1], t[2]) == 0) return 0;
    if (!valid_date(t[3])) return 0;
    if (strlen(t[4]) != 1 || t[4][0] < '1' || t[4][0] > '9') return 0;
    if (strcmp(t[5], "ECO") != 0 && strcmp(t[5], "BUS") != 0) return 0;
    if (nt == 7 && (!valid_date(t[6]) || strcmp(t[6], t[3]) < 0)) return 0;
    return 1;
}

int main(void) {
    char line[8192];
    while (fgets(line, sizeof line, stdin)) {
        size_t n = strlen(line);
        if (n && line[n - 1] == '\n') line[--n] = 0;
        if (n && line[n - 1] == '\r') line[--n] = 0;
        if (n == 0) continue;

        char *tok[MAXTOK + 1];
        int nt = 0;
        char *p = line;
        for (;;) {
            if (nt < MAXTOK) tok[nt] = p;
            nt++;
            char *sp = strchr(p, ' ');
            if (!sp) break;
            *sp = 0;
            p = sp + 1;
        }
        if (nt > MAXTOK) nt = MAXTOK + 1;  // quá nhiều thành phần: chắc chắn sai

        int is_search = strcmp(tok[0], "SEARCH") == 0;
        int is_account = strcmp(tok[0], "LOGIN") == 0 || strcmp(tok[0], "REGISTER") == 0;
        int ok = 0;
        if (nt <= MAXTOK) {
            if (is_search) ok = valid_search(tok, nt);
            else if (is_account) ok = nt == 3 && valid_user(tok[1]) && valid_pass(tok[2]);
        }
        int known = is_search || is_account;
        puts(!known ? "999 UNKNOWN ERROR" : ok ? "100 OK" : "201 INVALID");
    }
    return 0;
}
