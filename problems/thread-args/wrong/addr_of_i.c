// Sai có chủ đích: truyền &i (địa chỉ biến vòng lặp) cho mọi luồng, giống lỗi &client_socket trong pthread_server.c.
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>

long long a[200], sq[200];

void *worker(void *arg) {
    int i = *(int *)arg;
    sq[i] = a[i] * a[i];
    return NULL;
}

int main(void) {
    int n;
    if (scanf("%d", &n) != 1) {
        return 0;
    }
    for (int i = 0; i < n; i++) {
        scanf("%lld", &a[i]);
    }
    pthread_t tid[200];
    for (int i = 0; i < n; i++) {
        pthread_create(&tid[i], NULL, worker, &i);
    }
    for (int i = 0; i < n; i++) {
        pthread_join(tid[i], NULL);
    }
    for (int i = 0; i < n; i++) {
        printf("%lld\n", sq[i]);
    }
    return 0;
}
