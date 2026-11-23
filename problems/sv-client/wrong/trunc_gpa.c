// SAI có chủ đích: ép kiểu thẳng (unsigned short)(x*100) nên 2.85 thành 284.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>

int main(int argc, char *argv[]) {
    if (argc != 3) {
        printf("Usage: %s <ip> <port>\n", argv[0]);
        return 1;
    }
    int client_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(atoi(argv[2]));
    addr.sin_addr.s_addr = inet_addr(argv[1]);
    if (connect(client_socket, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
        perror("connect");
        close(client_socket);
        exit(EXIT_FAILURE);
    }

    char mssv_s[64], name[512], dob[64], gpa_s[64];
    while (fgets(mssv_s, sizeof(mssv_s), stdin) != NULL && fgets(name, sizeof(name), stdin) != NULL &&
           fgets(dob, sizeof(dob), stdin) != NULL && fgets(gpa_s, sizeof(gpa_s), stdin) != NULL) {
        // fgets giữ lại "\n" (hoặc "\r\n"): bỏ đi như udp_sender.c
        mssv_s[strcspn(mssv_s, "\r\n")] = 0;
        name[strcspn(name, "\r\n")] = 0;
        dob[strcspn(dob, "\r\n")] = 0;
        gpa_s[strcspn(gpa_s, "\r\n")] = 0;

        unsigned int mssv = 0, year = 0, month = 0, day = 0;
        double gpa = 0;
        sscanf(mssv_s, "%u", &mssv);
        sscanf(dob, "%u-%u-%u", &year, &month, &day);
        sscanf(gpa_s, "%lf", &gpa);
        unsigned short gpa100 = (unsigned short)(gpa * 100);
        int nlen = strlen(name);  // số BYTE (UTF-8), không phải số ký tự

        // Ghép từng trường vào mảng byte (không gửi thẳng struct: padding + thứ tự host).
        unsigned int net_mssv = htonl(mssv);
        unsigned short net_year = htons(year);
        unsigned short net_gpa = htons(gpa100);
        unsigned char record[4 + 1 + 255 + 6];
        int p = 0;
        memcpy(record + p, &net_mssv, 4);
        p += 4;
        record[p++] = nlen;
        memcpy(record + p, name, nlen);
        p += nlen;
        memcpy(record + p, &net_year, 2);
        p += 2;
        record[p++] = month;
        record[p++] = day;
        memcpy(record + p, &net_gpa, 2);
        p += 2;
        if (send(client_socket, record, p, 0) == -1) break;

        // Đọc một dòng phản hồi: có thể đến từng byte, nên recv từng byte tới khi gặp '\n'.
        char reply[128];
        int n = 0, closed = 0;
        while (n < (int)sizeof(reply) - 1) {
            char c;
            if (recv(client_socket, &c, 1, 0) <= 0) {
                closed = 1;
                break;
            }
            if (c == '\n') break;
            reply[n++] = c;
        }
        if (closed) break;  // server đóng mà không trả lời
        reply[n] = 0;
        printf("%s\n", reply);
        if (strcmp(reply, "OK") != 0) break;  // ERROR: server sẽ đóng kết nối
    }
    close(client_socket);
    return 0;
}
