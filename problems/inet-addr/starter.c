// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, string, arpa/inet)

int main(void) {
    char line[256];
    while (fgets(line, sizeof(line), stdin) != NULL) {
        line[strcspn(line, "\r\n")] = 0;
        // TODO: inet_addr(line) -> INADDR_NONE (trừ "255.255.255.255") thì INVALID;
        //       ngược lại VALID <inet_ntoa> 0x%08X <LOẠI> (nhớ ntohl trước khi in/so mặt nạ)
    }
    return 0;
}
