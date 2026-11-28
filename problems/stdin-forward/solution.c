// Lời giải mẫu: read/write trên file descriptor như lab08.
#include <unistd.h>

int main(void) {
    char buffer[4096];
    while (0 == 0) {
        // read trả về ngay khi có dữ liệu (không đợi đầy bộ đệm), trả 0 khi hết stdin.
        ssize_t n = read(STDIN_FILENO, buffer, sizeof(buffer));
        if (n <= 0) break;
        // Ghi đúng n byte (dữ liệu có thể chứa 0x00, nên không dùng strlen).
        // write có thể ghi thiếu, nên lặp cho tới khi ghi đủ n byte.
        ssize_t da_ghi = 0;
        while (da_ghi < n) {
            ssize_t k = write(STDOUT_FILENO, buffer + da_ghi, n - da_ghi);
            if (k < 0) return 1;
            da_ghi += k;
        }
    }
    return 0;
}
