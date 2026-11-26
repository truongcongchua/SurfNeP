// Sai có chủ đích: PRICE chỉ so tổng tiền (không có khóa phụ), nên các chuyến hòa giá in theo thứ tự tùy ý của qsort.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { char code[16], airline[8], from[8], to[8], date[16], dep[8], arr[8]; long long ep, bp; int es, bs; } F;
typedef struct { const F *f; int minutes; long long total; } R;
static F fl[1000];
static int n;
static int cmp(const void *x, const void *y) {
    const R *a = x, *b = y;
    return a->total < b->total ? -1 : a->total > b->total;
}
int main(void) {
    char line[512];
    FILE *f = fopen("flights.txt", "r");
    while (n < 1000 && fgets(line, sizeof line, f)) {
        F *p = &fl[n];
        if (sscanf(line, "%15s %7s %7s %7s %15s %7s %7s %lld %d %lld %d", p->code, p->airline, p->from, p->to, p->date, p->dep, p->arr, &p->ep, &p->es, &p->bp, &p->bs) == 11) n++;
    }
    fclose(f);
    static R rows[1000];
    while (fgets(line, sizeof line, stdin)) {
        line[strcspn(line, "\r\n")] = 0;
        char cmd[32], from[16], to[16], date[16], cls[16], crit[32];
        int pax;
        if (sscanf(line, "%31s %15s %15s %15s %d %15s %31s", cmd, from, to, date, &pax, cls, crit) != 7 || strcmp(cmd, "COMPARE")) continue;
        int k = 0, bus = !strcmp(cls, "BUS");
        for (int i = 0; i < n; i++) {
            if (strcmp(fl[i].from, from) || strcmp(fl[i].to, to) || strcmp(fl[i].date, date) || (bus ? fl[i].bs : fl[i].es) < pax) continue;
            int d = ((fl[i].arr[0] - '0') * 10 + fl[i].arr[1] - '0') * 60 + (fl[i].arr[3] - '0') * 10 + fl[i].arr[4] - '0' -
                    (((fl[i].dep[0] - '0') * 10 + fl[i].dep[1] - '0') * 60 + (fl[i].dep[3] - '0') * 10 + fl[i].dep[4] - '0');
            rows[k].f = &fl[i]; rows[k].minutes = d > 0 ? d : d + 1440; rows[k].total = (bus ? fl[i].bp : fl[i].ep) * pax; k++;
        }
        qsort(rows, (size_t)k, sizeof rows[0], cmp);
        printf("110 FLIGHTS %d\n", k);
        for (int i = 0; i < k; i++) printf("%s %s %s %s %d %lld\n", rows[i].f->code, rows[i].f->airline, rows[i].f->dep, rows[i].f->arr, rows[i].minutes, rows[i].total);
    }
    return 0;
}
