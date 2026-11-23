// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, stdint, stdio, string)

int main(void) {
    char line[256];
    while (fgets(line, sizeof line, stdin)) {
        // TODO: tách "u16 X" / "u32 X", kiểm tra hợp lệ
        // TODO: htons/htonl, memcpy ra mảng byte, in hex rồi " | " rồi giá trị
    }
    return 0;
}
