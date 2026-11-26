#include <stdio.h>
#include <string.h>

int main(void) {
    char line[8192];
    while (fgets(line, sizeof line, stdin)) {
        // TODO: bỏ '\n' rồi bỏ đúng một '\r' cuối dòng
        // TODO: dòng trống -> bỏ qua
        // TODO: tách theo đúng một dấu cách (không dùng strtok), kiểm tra tên lệnh rồi tham số
        // TODO: in "100 OK" / "201 INVALID" / "999 UNKNOWN ERROR"
    }
    return 0;
}
