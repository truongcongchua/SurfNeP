#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_FLIGHTS 1000

typedef struct {
    char code[16], airline[8], from[8], to[8], date[16], dep[8], arr[8];
    long long eco_price, bus_price;
    int eco_seats, bus_seats;
} Flight;

// Gợi ý: một dòng kết quả = chuyến bay + số phút bay + tổng tiền; sắp xếp mảng các dòng này bằng qsort.
typedef struct { const Flight *f; int minutes; long long total; } Row;

int main(void) {
    static Flight fl[MAX_FLIGHTS];
    int n = 0;
    // TODO: nạp flights.txt một lần (fopen + fgets + sscanf, như bài flight-filter)
    char line[512];
    while (fgets(line, sizeof line, stdin)) {
        // TODO: bỏ '\r' '\n', bỏ qua dòng trống
        // TODO: COMPARE <đi> <đến> <ngày> <khách> <hạng> <tiêu chí>: lọc rồi qsort với hàm so sánh theo tiêu chí
        // TODO: BEST ...: mỗi hãng một dòng, chuyến rẻ nhất và nhanh nhất
    }
    (void)n;
    return 0;
}
