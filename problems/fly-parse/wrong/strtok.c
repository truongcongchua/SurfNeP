// Sai có chủ đích: dùng strtok nên nhiều dấu cách liền nhau bị coi là một, dấu cách thừa bị bỏ qua.
#include <stdio.h>
#include <string.h>
int main(void) {
    char line[8192];
    while (fgets(line, sizeof line, stdin)) {
        line[strcspn(line, "\r\n")] = 0;
        if (!line[0]) continue;
        char *t[8]; int n = 0;
        for (char *p = strtok(line, " "); p && n < 8; p = strtok(NULL, " ")) t[n++] = p;
        if (n == 0) { puts("999 UNKNOWN ERROR"); continue; }
        if (!strcmp(t[0], "LOGIN") || !strcmp(t[0], "REGISTER")) puts(n == 3 && strlen(t[1]) <= 32 && strlen(t[2]) >= 4 ? "100 OK" : "201 INVALID");
        else if (!strcmp(t[0], "SEARCH")) puts(n == 6 || n == 7 ? "100 OK" : "201 INVALID");
        else puts("999 UNKNOWN ERROR");
    }
    return 0;
}
