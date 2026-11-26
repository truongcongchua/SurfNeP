#include <stdio.h>
#include <string.h>

#define MAX_FLIGHTS 1000

typedef struct {
    char code[16], airline[8], from[8], to[8], date[16], dep[8], arr[8];
    long long eco_price, bus_price;
    int eco_seats, bus_seats;
} Flight;

int main(void) {
    static Flight fl[MAX_FLIGHTS];
    int n = 0;
    // TODO: mở flights.txt, đọc từng dòng (fgets + sscanf) vào fl[]
    char line[256];
    while (fgets(line, sizeof line, stdin)) {
        // TODO: bỏ '\r', '\n'; bỏ qua dòng trống
        // TODO: tách 5 trường của truy vấn; duyệt fl[] theo thứ tự, in "110 FLIGHTS k" rồi k dòng
    }
    (void)n;
    return 0;
}
