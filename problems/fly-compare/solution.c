// Lời giải mẫu: nạp flights.txt một lần; lọc rồi qsort với hàm so sánh theo tiêu chí (khóa phụ rõ ràng).
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_FLIGHTS 1000

typedef struct {
    char code[16], airline[8], from[8], to[8], date[16], dep[8], arr[8];
    long long eco_price, bus_price;
    int eco_seats, bus_seats;
} Flight;

typedef struct { const Flight *f; int minutes; long long total; } Row;

static Flight fl[MAX_FLIGHTS];
static int nfl;

static int mins(const char *t) { return ((t[0] - '0') * 10 + (t[1] - '0')) * 60 + (t[3] - '0') * 10 + (t[4] - '0'); }

static int duration(const Flight *f) {
    int d = mins(f->arr) - mins(f->dep);
    return d > 0 ? d : d + 1440;
}

static int cmp_ll(long long a, long long b) { return a < b ? -1 : a > b; }

static int cmp_price(const void *x, const void *y) {
    const Row *a = x, *b = y;
    int c = cmp_ll(a->total, b->total);
    if (!c) c = cmp_ll(a->minutes, b->minutes);
    return c ? c : strcmp(a->f->code, b->f->code);
}
static int cmp_duration(const void *x, const void *y) {
    const Row *a = x, *b = y;
    int c = cmp_ll(a->minutes, b->minutes);
    if (!c) c = cmp_ll(a->total, b->total);
    return c ? c : strcmp(a->f->code, b->f->code);
}
static int cmp_depart(const void *x, const void *y) {
    const Row *a = x, *b = y;
    int c = strcmp(a->f->dep, b->f->dep);
    return c ? c : strcmp(a->f->code, b->f->code);
}
static int cmp_airline_then_code(const void *x, const void *y) {
    const Row *a = x, *b = y;
    int c = strcmp(a->f->airline, b->f->airline);
    return c ? c : strcmp(a->f->code, b->f->code);
}

static int collect(Row *rows, const char *from, const char *to, const char *date, int pax, int bus) {
    int k = 0;
    for (int i = 0; i < nfl; i++) {
        int seats = bus ? fl[i].bus_seats : fl[i].eco_seats;
        if (strcmp(fl[i].from, from) || strcmp(fl[i].to, to) || strcmp(fl[i].date, date) || seats < pax) continue;
        rows[k].f = &fl[i];
        rows[k].minutes = duration(&fl[i]);
        rows[k].total = (bus ? fl[i].bus_price : fl[i].eco_price) * pax;
        k++;
    }
    return k;
}

int main(void) {
    FILE *f = fopen("flights.txt", "r");
    if (!f) { perror("flights.txt"); return 1; }
    char line[512];
    while (nfl < MAX_FLIGHTS && fgets(line, sizeof line, f)) {
        Flight *x = &fl[nfl];
        if (sscanf(line, "%15s %7s %7s %7s %15s %7s %7s %lld %d %lld %d", x->code, x->airline, x->from, x->to, x->date, x->dep,
                   x->arr, &x->eco_price, &x->eco_seats, &x->bus_price, &x->bus_seats) == 11)
            nfl++;
    }
    fclose(f);

    static Row rows[MAX_FLIGHTS];
    while (fgets(line, sizeof line, stdin)) {
        size_t len = strlen(line);
        if (len && line[len - 1] == '\n') line[--len] = 0;
        if (len && line[len - 1] == '\r') line[--len] = 0;
        if (len == 0) continue;
        char cmd[32], from[16], to[16], date[16], cls[16], crit[32] = "";
        int pax, got = sscanf(line, "%31s %15s %15s %15s %d %15s %31s", cmd, from, to, date, &pax, cls, crit);
        int is_compare = !strcmp(cmd, "COMPARE") && got == 7, is_best = !strcmp(cmd, "BEST") && got == 6;
        if (!is_compare && !is_best) { puts("999 UNKNOWN ERROR"); continue; }
        int bus = !strcmp(cls, "BUS");
        int k = collect(rows, from, to, date, pax, bus);

        if (is_compare) {
            int (*cmp)(const void *, const void *) = NULL;
            if (!strcmp(crit, "PRICE")) cmp = cmp_price;
            else if (!strcmp(crit, "DURATION")) cmp = cmp_duration;
            else if (!strcmp(crit, "DEPART")) cmp = cmp_depart;
            if (!cmp) { puts("201 INVALID"); continue; }
            qsort(rows, (size_t)k, sizeof rows[0], cmp);
            printf("110 FLIGHTS %d\n", k);
            for (int i = 0; i < k; i++)
                printf("%s %s %s %s %d %lld\n", rows[i].f->code, rows[i].f->airline, rows[i].f->dep, rows[i].f->arr,
                       rows[i].minutes, rows[i].total);
        } else {
            qsort(rows, (size_t)k, sizeof rows[0], cmp_airline_then_code);
            int groups = 0;
            for (int i = 0; i < k; i++)
                if (i == 0 || strcmp(rows[i].f->airline, rows[i - 1].f->airline)) groups++;
            printf("110 AIRLINES %d\n", groups);
            for (int i = 0; i < k;) {
                int j = i;
                while (j < k && !strcmp(rows[j].f->airline, rows[i].f->airline)) j++;
                int cheap = i, fast = i;
                for (int t = i; t < j; t++) {  // rows đã theo mã tăng dần trong cùng hãng: so sánh chặt giữ mã nhỏ nhất
                    if (rows[t].total < rows[cheap].total) cheap = t;
                    if (rows[t].minutes < rows[fast].minutes) fast = t;
                }
                printf("%s CHEAPEST %s %lld FASTEST %s %d\n", rows[i].f->airline, rows[cheap].f->code, rows[cheap].total,
                       rows[fast].f->code, rows[fast].minutes);
                i = j;
            }
        }
    }
    return 0;
}
