// SAI có chủ đích: fread đòi đủ 4096 byte (hoặc EOF) mới trả về -> dữ liệu đến chậm bị giữ lại.
#include <stdio.h>
#include <unistd.h>

int main(void) {
    char buffer[4096];
    size_t n;
    while ((n = fread(buffer, 1, sizeof(buffer), stdin)) > 0) {
        write(STDOUT_FILENO, buffer, n);
    }
    return 0;
}
