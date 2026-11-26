// Sai có chủ đích: đọc bàn phím bằng fgets (chặn) nên không in được thông báo khi chờ người dùng gõ.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc != 3) return 1;
    int s = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = inet_addr(argv[1]);
    a.sin_port = htons(atoi(argv[2]));
    if (connect(s, (struct sockaddr *)&a, sizeof a) < 0) return 1;
    char buf[1024], line[256];
    recv(s, buf, sizeof buf, 0);
    for (;;) {
        printf("=== FLY ===\n1. Dang nhap\n2. Tim chuyen\n3. Dat ve\n4. Ve cua toi\n5. Thoat\nChon: ");
        fflush(stdout);
        if (!fgets(line, sizeof line, stdin)) { send(s, "QUIT\n", 5, 0); return 0; }
        if (line[0] == '5') { send(s, "QUIT\n", 5, 0); return 0; }
        printf("Lua chon khong hop le\n");
    }
}
