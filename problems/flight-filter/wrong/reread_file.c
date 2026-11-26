// Sai có chủ đích: mở và đọc lại flights.txt cho MỖI truy vấn (đúng kết quả nhưng quá chậm với hàng chục nghìn truy vấn).
#include <stdio.h>
#include <string.h>

int main(void) {
    char line[512];
    static char out[400000];
    while (fgets(line, sizeof line, stdin)) {
        char from[16], to[16], date[16], cls[16];
        int pax;
        line[strcspn(line, "\r\n")] = 0;
        if (!line[0] || sscanf(line, "%15s %15s %15s %d %15s", from, to, date, &pax, cls) != 5) continue;
        FILE *f = fopen("flights.txt", "r");
        out[0] = 0;
        char l2[512];
        int k = 0;
        size_t o = 0;
        while (fgets(l2, sizeof l2, f)) {
            char c[16], a[8], fr[8], t[8], d[16], dep[8], arr[8];
            long long ep, bp;
            int es, bs;
            if (sscanf(l2, "%15s %7s %7s %7s %15s %7s %7s %lld %d %lld %d", c, a, fr, t, d, dep, arr, &ep, &es, &bp, &bs) != 11)
                continue;
            int bus = !strcmp(cls, "BUS");
            if (!strcmp(fr, from) && !strcmp(t, to) && !strcmp(d, date) && (bus ? bs : es) >= pax) {
                o += sprintf(out + o, "%s %s %s %s %lld\n", c, a, dep, arr, (bus ? bp : ep) * pax);
                k++;
            }
        }
        fclose(f);
        printf("110 FLIGHTS %d\n%s", k, out);
    }
    return 0;
}
