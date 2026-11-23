// Lời giải mẫu: server lặp như tcp_server.c; mỗi thông điệp = 4 byte độ dài (thứ tự mạng) + dữ liệu.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>

#define MAX_LEN 65536

unsigned char data[MAX_LEN];

void serve(int client) {
    while (0 == 0) {
        // 1. Đọc đủ 4 byte độ dài: recv có thể trả về ít hơn số byte yêu cầu, nên phải lặp.
        unsigned int netlen;
        int got = 0;
        while (got < 4) {
            int k = recv(client, (char *)&netlen + got, 4 - got, 0);
            if (k <= 0) return;  // client đóng hoặc lỗi
            got += k;
        }
        unsigned int len = ntohl(netlen);  // số không dấu: 0xFFFFFFFF không thành số âm
        if (len > MAX_LEN) return;         // sai giao thức: đóng kết nối

        // 2. Đọc đủ len byte dữ liệu, cũng bằng vòng lặp.
        unsigned int have = 0;
        while (have < len) {
            int k = recv(client, data + have, len - have, 0);
            if (k <= 0) return;
            have += k;
        }

        for (unsigned int i = 0; i < len; i++)
            if (data[i] >= 'a' && data[i] <= 'z') data[i] = data[i] - 'a' + 'A';

        // 3. Gửi lại cùng định dạng (socket blocking: send chờ tới khi gửi hết).
        send(client, &netlen, 4, 0);
        if (len > 0) send(client, data, len, 0);
    }
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    int listener = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    int opt = 1;
    setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(atoi(argv[1]));
    addr.sin_addr.s_addr = INADDR_ANY;
    if (bind(listener, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
        perror("bind() failed");
        return 1;
    }
    if (listen(listener, 5) == -1) {
        perror("listen() failed");
        return 1;
    }
    while (0 == 0) {
        int client = accept(listener, NULL, NULL);
        if (client == -1) continue;
        serve(client);
        close(client);
    }
}
