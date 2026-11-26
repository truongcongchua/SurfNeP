// Lời giải mẫu: nạp flights.txt một lần vào mảng struct, mỗi truy vấn duyệt mảng theo thứ tự tệp.
#include <stdio.h>
#include <string.h>

#define MAX_FLIGHTS 1000

typedef struct {
    char code[16], airline[8], from[8], to[8], date[16], dep[8], arr[8];
    long long eco_price, bus_price;
    int eco_seats, bus_seats;
} Flight;

static Flight fl[MAX_FLIGHTS];

int main(void) {
    int n = 0;
    FILE *f = fopen("flights.txt", "r");
    if (!f) { perror("flights.txt"); return 1; }
    char line[512];
    while (n < MAX_FLIGHTS && fgets(line, sizeof line, f)) {
        Flight *x = &fl[n];
        if (sscanf(line, "%15s %7s %7s %7s %15s %7s %7s %lld %d %lld %d", x->code, x->airline, x->from, x->to,
                   x->date, x->dep, x->arr, &x->eco_price, &x->eco_seats, &x->bus_price, &x->bus_seats) == 11)
            n++;
    }
    fclose(f);

    while (fgets(line, sizeof line, stdin)) {
        size_t len = strlen(line);
        if (len && line[len - 1] == '\n') line[--len] = 0;
        if (len && line[len - 1] == '\r') line[--len] = 0;
        if (len == 0) continue;
        char from[16], to[16], date[16], cls[16];
        int pax;
        if (sscanf(line, "%15s %15s %15s %d %15s", from, to, date, &pax, cls) != 5) continue;
        int bus = strcmp(cls, "BUS") == 0;

        int idx[MAX_FLIGHTS], k = 0;
        for (int i = 0; i < n; i++) {
            int seats = bus ? fl[i].bus_seats : fl[i].eco_seats;
            if (!strcmp(fl[i].from, from) && !strcmp(fl[i].to, to) && !strcmp(fl[i].date, date) && seats >= pax)
                idx[k++] = i;
        }
        printf("110 FLIGHTS %d\n", k);
        for (int j = 0; j < k; j++) {
            Flight *x = &fl[idx[j]];
            long long price = bus ? x->bus_price : x->eco_price;
            printf("%s %s %s %s %lld\n", x->code, x->airline, x->dep, x->arr, price * pax);
        }
    }
    return 0;
}
