// SAI có chủ đích: fgets + fputs dừng ở byte 0x00 và chỉ ghi ra khi đủ một dòng.
#include <stdio.h>

int main(void) {
    char line[4096];
    while (fgets(line, sizeof(line), stdin) != NULL) {
        fputs(line, stdout);
        fflush(stdout);
    }
    return 0;
}
