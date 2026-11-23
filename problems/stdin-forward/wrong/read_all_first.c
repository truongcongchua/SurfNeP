// SAI có chủ đích: đọc hết stdin rồi mới ghi -> trượt test "ghi ngay khi đọc được".
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    size_t cap = 1 << 23, len = 0;
    char *all = malloc(cap);
    ssize_t n;
    while ((n = read(STDIN_FILENO, all + len, cap - len)) > 0) len += (size_t)n;
    write(STDOUT_FILENO, all, len);
    return 0;
}
