// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, pthread)

long long a[200], sq[200];

void *worker(void *arg) {
    // TODO: lấy chỉ số i từ arg, free(arg), sq[i] = a[i] * a[i], return NULL
    return NULL;
}

int main(void) {
    int n;
    // TODO: scanf n và n số vào a[]
    // TODO: vòng 1: với mỗi i, malloc một int chứa i, pthread_create(&tid[i], NULL, worker, p)
    // TODO: vòng 2: pthread_join từng luồng
    // TODO: in sq[0..n-1], mỗi số một dòng (%lld)
    return 0;
}
