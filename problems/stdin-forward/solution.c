// Lời giải mẫu: read/write trên file descriptor như lab08.
#include <unistd.h>

int main(void) {
    char buffer[4096];
    while (0 == 0) {
        // read trả về ngay khi có dữ liệu (không đợi đầy bộ đệm), trả 0 khi hết stdin.
        ssize_t n = read(STDIN_FILENO, buffer, sizeof(buffer));
        if (n <= 0) break;
        // Ghi đúng n byte (dữ liệu có thể chứa 0x00, nên không dùng strlen).
        write(STDOUT_FILENO, buffer, n);
    }
    return 0;
}
