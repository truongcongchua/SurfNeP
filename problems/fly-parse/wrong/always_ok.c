// Sai có chủ đích: chỉ kiểm tra tên lệnh và số thành phần, không kiểm tra nội dung.
#include <stdio.h>
#include <string.h>
int main(void) {
    char line[8192];
    while (fgets(line, sizeof line, stdin)) {
        line[strcspn(line, "\r\n")] = 0;
        if (!line[0]) continue;
        int sp = 0;
        for (char *p = line; *p; p++) sp += *p == ' ';
        if (!strncmp(line, "LOGIN ", 6) || !strncmp(line, "REGISTER ", 9)) puts(sp == 2 ? "100 OK" : "201 INVALID");
        else if (!strncmp(line, "SEARCH ", 7)) puts(sp == 5 || sp == 6 ? "100 OK" : "201 INVALID");
        else puts("999 UNKNOWN ERROR");
    }
    return 0;
}
