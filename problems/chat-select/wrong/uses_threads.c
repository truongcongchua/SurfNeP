// SAI có chủ đích: dùng pthread thay vì select() -> phải bị CV (Constraint Violation).
#include <pthread.h>
#include <stdio.h>

static void *worker(void *arg) { return arg; }

int main(void) {
    pthread_t t;
    pthread_create(&t, NULL, worker, NULL);
    pthread_join(t, NULL);
    return 0;
}
