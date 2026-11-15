#include <arpa/inet.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    char line[256];
    while (fgets(line, sizeof line, stdin)) {
        line[strcspn(line, "\r\n")] = 0;
        // TODO: inet_pton -> INVALID / VALID <inet_ntop> 0x%08X <LOẠI>
    }
    return 0;
}
