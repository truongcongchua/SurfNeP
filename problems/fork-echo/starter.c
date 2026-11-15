#include <arpa/inet.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>
#include <signal.h>
#include <sys/wait.h>

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen
    // TODO: SIGCHLD + waitpid để dọn zombie; vòng lặp accept -> fork; con echo rồi _exit, cha close(client)
    return 0;
}
