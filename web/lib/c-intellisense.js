// Gợi ý code cho editor C (Monaco): completion, snippet, signature help, hover, đi tới định nghĩa, kiểm tra ngoặc.
// Danh sách hàm chỉ gồm những gì xuất hiện trong code mẫu của thầy (IT4062) — khớp quy tắc "teacher toolkit".
// Provider đăng ký một lần cho cả trang; mỗi lần gọi đều đọc cfg() nên bật/tắt trong Cài đặt có hiệu lực ngay.

/* ---------- dữ liệu ---------- */

// [tên, kiểu trả về, "tham số", mô tả, header]
const FN = [
  ["socket", "int", "int domain, int type, int protocol", "Tạo socket. Trả về fd, -1 nếu lỗi. TCP: SOCK_STREAM, UDP: SOCK_DGRAM.", "sys/socket.h"],
  ["bind", "int", "int sockfd, const struct sockaddr *addr, socklen_t addrlen", "Gán địa chỉ (IP, port) cho socket. Ép &addr về (struct sockaddr *).", "sys/socket.h"],
  ["listen", "int", "int sockfd, int backlog", "Đặt socket TCP vào chế độ chờ kết nối. backlog = độ dài hàng đợi.", "sys/socket.h"],
  ["accept", "int", "int sockfd, struct sockaddr *addr, socklen_t *addrlen", "Nhận một kết nối đang chờ, trả về fd mới cho client đó. Chặn nếu chưa có ai kết nối.", "sys/socket.h"],
  ["connect", "int", "int sockfd, const struct sockaddr *addr, socklen_t addrlen", "Client kết nối tới server. Trả về 0 nếu thành công.", "sys/socket.h"],
  ["send", "ssize_t", "int sockfd, const void *buf, size_t len, int flags", "Gửi dữ liệu qua socket TCP. Trả về số byte đã gửi, -1 nếu lỗi.", "sys/socket.h"],
  ["recv", "ssize_t", "int sockfd, void *buf, size_t len, int flags", "Nhận dữ liệu. Trả về số byte đọc được, 0 nếu đối phương đóng kết nối, -1 nếu lỗi. TCP là luồng byte nên một lần recv có thể không đủ một dòng/gói.", "sys/socket.h"],
  ["sendto", "ssize_t", "int sockfd, const void *buf, size_t len, int flags, const struct sockaddr *dest_addr, socklen_t addrlen", "Gửi một datagram UDP tới địa chỉ chỉ định.", "sys/socket.h"],
  ["recvfrom", "ssize_t", "int sockfd, void *buf, size_t len, int flags, struct sockaddr *src_addr, socklen_t *addrlen", "Nhận một datagram UDP và lấy địa chỉ người gửi. Nhớ gán *addrlen = sizeof(...) trước khi gọi.", "sys/socket.h"],
  ["setsockopt", "int", "int sockfd, int level, int optname, const void *optval, socklen_t optlen", "Đặt tuỳ chọn socket. Ví dụ SOL_SOCKET + SO_REUSEADDR để bind lại cổng ngay.", "sys/socket.h"],
  ["select", "int", "int nfds, fd_set *readfds, fd_set *writefds, fd_set *exceptfds, struct timeval *timeout", "Chờ nhiều fd cùng lúc. nfds = fd lớn nhất + 1. Trả về số fd sẵn sàng. Mỗi vòng lặp phải dựng lại fd_set.", "sys/select.h"],
  ["ioctl", "int", "int fd, unsigned long request, ...", "Điều khiển thiết bị/socket. Ví dụ ioctl(fd, FIONBIO, &on) để chuyển sang non-blocking.", "sys/ioctl.h"],
  ["close", "int", "int fd", "Đóng file descriptor / socket.", "unistd.h"],
  ["open", "int", "const char *path, int flags, ... /* mode_t mode */", "Mở tệp, trả về fd (-1 nếu lỗi). Đọc: open(path, O_RDONLY). Ghi nối tiếp: open(path, O_WRONLY | O_CREAT | O_APPEND, 0644) — có O_CREAT thì phải thêm tham số quyền. Dùng xong phải close(fd).", "fcntl.h"],
  ["read", "ssize_t", "int fd, void *buf, size_t count", "Đọc tối đa count byte từ fd (tệp, socket, stdin). Trả về số byte đọc được, 0 khi hết dữ liệu (EOF), -1 nếu lỗi. Dữ liệu có thể chứa '\0': dùng đúng số byte trả về, đừng dùng strlen.", "unistd.h"],
  ["write", "ssize_t", "int fd, const void *buf, size_t count", "Ghi count byte ra fd. Trả về số byte đã ghi, -1 nếu lỗi. Không có bộ đệm của thư viện: dữ liệu vào tệp ngay.", "unistd.h"],
  ["htons", "uint16_t", "uint16_t hostshort", "Đổi số 16 bit (port) từ thứ tự byte máy sang thứ tự mạng.", "arpa/inet.h"],
  ["ntohs", "uint16_t", "uint16_t netshort", "Đổi số 16 bit từ thứ tự byte mạng sang thứ tự máy.", "arpa/inet.h"],
  ["htonl", "uint32_t", "uint32_t hostlong", "Đổi số 32 bit sang thứ tự byte mạng. Ví dụ htonl(INADDR_ANY).", "arpa/inet.h"],
  ["inet_addr", "in_addr_t", "const char *cp", "Đổi chuỗi IPv4 \"a.b.c.d\" thành số 32 bit thứ tự mạng.", "arpa/inet.h"],
  ["inet_ntoa", "char *", "struct in_addr in", "Đổi địa chỉ IPv4 thành chuỗi \"a.b.c.d\" (buffer tĩnh, không free).", "arpa/inet.h"],
  ["inet_ntop", "const char *", "int af, const void *src, char *dst, socklen_t size", "Đổi địa chỉ nhị phân thành chuỗi vào dst.", "arpa/inet.h"],
  ["getaddrinfo", "int", "const char *node, const char *service, const struct addrinfo *hints, struct addrinfo **res", "Phân giải tên miền/dịch vụ thành danh sách địa chỉ. Dùng xong phải freeaddrinfo.", "netdb.h"],
  ["freeaddrinfo", "void", "struct addrinfo *res", "Giải phóng danh sách do getaddrinfo cấp.", "netdb.h"],
  ["fork", "pid_t", "void", "Tạo tiến trình con. Trả về 0 trong con, pid con trong cha, -1 nếu lỗi.", "unistd.h"],
  ["wait", "pid_t", "int *wstatus", "Chờ một tiến trình con kết thúc (thu hồi zombie).", "sys/wait.h"],
  ["waitpid", "pid_t", "pid_t pid, int *wstatus, int options", "Chờ tiến trình con cụ thể. waitpid(-1, NULL, WNOHANG) không chặn — dùng trong handler SIGCHLD.", "sys/wait.h"],
  ["getpid", "pid_t", "void", "Lấy pid của tiến trình hiện tại.", "unistd.h"],
  ["signal", "sighandler_t", "int signum, void (*handler)(int)", "Đăng ký hàm xử lý tín hiệu. Ví dụ signal(SIGCHLD, handler).", "signal.h"],
  ["sleep", "unsigned int", "unsigned int seconds", "Ngủ theo số giây.", "unistd.h"],
  ["exit", "void", "int status", "Kết thúc chương trình.", "stdlib.h"],
  ["pthread_create", "int", "pthread_t *thread, const pthread_attr_t *attr, void *(*start_routine)(void *), void *arg", "Tạo thread chạy start_routine(arg). Trả về 0 nếu thành công. Nên truyền arg là vùng nhớ riêng cho mỗi thread (malloc).", "pthread.h"],
  ["pthread_join", "int", "pthread_t thread, void **retval", "Chờ thread kết thúc.", "pthread.h"],
  ["pthread_detach", "int", "pthread_t thread", "Cho thread tự thu hồi tài nguyên khi kết thúc (không cần join).", "pthread.h"],
  ["pthread_self", "pthread_t", "void", "Lấy id của thread hiện tại.", "pthread.h"],
  ["pthread_mutex_lock", "int", "pthread_mutex_t *mutex", "Khoá mutex (chặn nếu đang bị giữ).", "pthread.h"],
  ["pthread_mutex_unlock", "int", "pthread_mutex_t *mutex", "Mở khoá mutex.", "pthread.h"],
  ["printf", "int", "const char *format, ...", "In ra stdout theo định dạng.", "stdio.h"],
  ["fprintf", "int", "FILE *stream, const char *format, ...", "In ra stream (stderr, file...).", "stdio.h"],
  ["sprintf", "int", "char *str, const char *format, ...", "In vào buffer. Dễ tràn buffer, ưu tiên snprintf.", "stdio.h"],
  ["snprintf", "int", "char *str, size_t size, const char *format, ...", "In vào buffer, tối đa size byte (kể cả '\\0').", "stdio.h"],
  ["sscanf", "int", "const char *str, const char *format, ...", "Đọc dữ liệu có định dạng từ chuỗi. Trả về số trường đọc được.", "stdio.h"],
  ["fgets", "char *", "char *s, int size, FILE *stream", "Đọc tối đa size-1 ký tự hoặc tới hết dòng (giữ '\\n'). NULL khi hết dữ liệu.", "stdio.h"],
  ["fflush", "int", "FILE *stream", "Đẩy bộ đệm ra ngay (ví dụ fflush(stdout), hoặc để dữ liệu fwrite vào tệp ngay mà chưa đóng).", "stdio.h"],
  ["fopen", "FILE *", "const char *path, const char *mode", "Mở tệp. NULL nếu lỗi. Chế độ: \"rb\" đọc nhị phân, \"wb\" ghi (xoá nội dung cũ), \"ab\" ghi nối vào cuối (tạo mới nếu chưa có). Dữ liệu có thể chứa 0x00 nên luôn thêm 'b'.", "stdio.h"],
  ["fread", "size_t", "void *ptr, size_t size, size_t nmemb, FILE *stream", "Đọc tối đa nmemb phần tử, mỗi phần tử size byte. Với size = 1 thì kết quả là số byte đọc được; 0 khi hết tệp. Ví dụ: while ((n = fread(buf, 1, sizeof(buf), f)) > 0) send(fd, buf, n, 0);", "stdio.h"],
  ["fwrite", "size_t", "const void *ptr, size_t size, size_t nmemb, FILE *stream", "Ghi nmemb phần tử, mỗi phần tử size byte. Với size = 1 thì ghi đúng n byte (an toàn với 0x00, khác fputs/strlen). Dữ liệu nằm trong bộ đệm cho tới khi fflush/fclose.", "stdio.h"],
  ["fclose", "int", "FILE *stream", "Đẩy dữ liệu còn trong bộ đệm xuống tệp rồi đóng. Quên fclose thì rò rỉ fd (giới hạn 256) và dữ liệu có thể chưa nằm trong tệp.", "stdio.h"],
  ["perror", "void", "const char *s", "In s kèm mô tả lỗi của errno ra stderr.", "stdio.h"],
  ["strlen", "size_t", "const char *s", "Độ dài chuỗi (không tính '\\0').", "string.h"],
  ["strcmp", "int", "const char *s1, const char *s2", "So sánh chuỗi. Trả về 0 nếu bằng nhau.", "string.h"],
  ["strncmp", "int", "const char *s1, const char *s2, size_t n", "So sánh tối đa n ký tự đầu.", "string.h"],
  ["strstr", "char *", "const char *haystack, const char *needle", "Tìm chuỗi con. NULL nếu không thấy.", "string.h"],
  ["strchr", "char *", "const char *s, int c", "Tìm ký tự đầu tiên. NULL nếu không thấy.", "string.h"],
  ["strcat", "char *", "char *dest, const char *src", "Nối src vào cuối dest (dest phải đủ chỗ).", "string.h"],
  ["strncpy", "char *", "char *dest, const char *src, size_t n", "Chép tối đa n ký tự. Có thể không tự thêm '\\0'.", "string.h"],
  ["strerror", "char *", "int errnum", "Mô tả lỗi dạng chuỗi.", "string.h"],
  ["memset", "void *", "void *s, int c, size_t n", "Gán n byte đầu bằng c. Ví dụ memset(&addr, 0, sizeof(addr)).", "string.h"],
  ["memcpy", "void *", "void *dest, const void *src, size_t n", "Chép n byte (vùng nhớ không chồng nhau).", "string.h"],
  ["memmove", "void *", "void *dest, const void *src, size_t n", "Chép n byte, an toàn khi hai vùng chồng nhau.", "string.h"],
  ["malloc", "void *", "size_t size", "Cấp phát size byte trên heap. NULL nếu hết bộ nhớ.", "stdlib.h"],
  ["free", "void", "void *ptr", "Giải phóng vùng nhớ do malloc cấp.", "stdlib.h"],
  ["atoi", "int", "const char *nptr", "Đổi chuỗi sang int.", "stdlib.h"],
  ["stat", "int", "const char *path, struct stat *buf", "Lấy thông tin file.", "sys/stat.h"],
  ["access", "int", "const char *path, int mode", "Kiểm tra file có tồn tại / quyền truy cập.", "unistd.h"],
  ["opendir", "DIR *", "const char *name", "Mở thư mục.", "dirent.h"],
  ["readdir", "struct dirent *", "DIR *dirp", "Đọc mục kế tiếp trong thư mục. NULL khi hết.", "dirent.h"],
].map(([name, ret, params, doc, header]) => ({
  kind: "fn", name, ret, params, doc, header,
  sig: `${ret} ${name}(${params})`,
  args: params === "void" ? [] : params.split(/,\s*/),
}));

// Macro dạng hàm: FD_*.
const MACROS = [
  ["FD_ZERO", "fd_set *set", "Xoá rỗng tập fd. Gọi đầu mỗi vòng lặp select.", "sys/select.h"],
  ["FD_SET", "int fd, fd_set *set", "Thêm fd vào tập.", "sys/select.h"],
  ["FD_CLR", "int fd, fd_set *set", "Bỏ fd khỏi tập.", "sys/select.h"],
  ["FD_ISSET", "int fd, fd_set *set", "Kiểm tra fd có sẵn sàng sau select không.", "sys/select.h"],
].map(([name, params, doc, header]) => ({ kind: "fn", name, ret: "", params, doc, header, sig: `${name}(${params})`, args: params.split(/,\s*/) }));

// Hằng số.
const CONSTS = [
  ["AF_INET", "Họ địa chỉ IPv4."], ["SOCK_STREAM", "Kiểu socket TCP (luồng byte)."], ["SOCK_DGRAM", "Kiểu socket UDP (datagram)."],
  ["INADDR_ANY", "Nghe trên mọi địa chỉ IP của máy (0.0.0.0). Dùng htonl(INADDR_ANY)."],
  ["SOL_SOCKET", "Mức tuỳ chọn cho setsockopt."], ["SO_REUSEADDR", "Cho phép bind lại cổng đang ở TIME_WAIT."],
  ["FIONBIO", "Request của ioctl để bật/tắt chế độ non-blocking."],
  ["SIGCHLD", "Tín hiệu gửi cho cha khi con kết thúc."], ["SIGINT", "Tín hiệu ngắt (Ctrl+C)."], ["WNOHANG", "Cờ cho waitpid: không chặn nếu chưa có con nào kết thúc."],
  ["O_RDONLY", "Cờ open: chỉ đọc."], ["O_WRONLY", "Cờ open: chỉ ghi."],
  ["O_CREAT", "Cờ open: tạo tệp nếu chưa có (phải thêm tham số quyền, ví dụ 0644)."],
  ["O_APPEND", "Cờ open: mọi lần ghi nối vào cuối tệp, không ghi đè dữ liệu cũ."], ["O_TRUNC", "Cờ open: cắt tệp về 0 byte khi mở (xoá dữ liệu cũ)."],
  ["NULL", "Con trỏ rỗng."], ["STDIN_FILENO", "fd 0."], ["STDOUT_FILENO", "fd 1."], ["PTHREAD_MUTEX_INITIALIZER", "Giá trị khởi tạo tĩnh cho pthread_mutex_t."],
  ["stdin", "Luồng nhập chuẩn."], ["stdout", "Luồng xuất chuẩn."], ["stderr", "Luồng lỗi chuẩn."],
].map(([name, doc]) => ({ kind: "const", name, doc, sig: name }));

// Kiểu dữ liệu và trường của struct.
const TYPES = [
  ["struct sockaddr_in", "Địa chỉ IPv4: sin_family, sin_port, sin_addr.s_addr.", ["sin_family", "sin_port", "sin_addr", "s_addr"]],
  ["struct sockaddr", "Địa chỉ socket tổng quát; ép kiểu từ sockaddr_in khi gọi bind/connect/accept.", []],
  ["struct in_addr", "Địa chỉ IPv4 32 bit (trường s_addr).", []],
  ["struct timeval", "Thời gian: tv_sec (giây), tv_usec (micro giây). Dùng cho timeout của select.", ["tv_sec", "tv_usec"]],
  ["struct addrinfo", "Kết quả/gợi ý cho getaddrinfo.", ["ai_family", "ai_socktype", "ai_flags", "ai_addr", "ai_addrlen", "ai_next"]],
  ["socklen_t", "Kiểu độ dài địa chỉ socket.", []], ["fd_set", "Tập file descriptor cho select.", []],
  ["pthread_t", "Định danh thread.", []], ["pthread_mutex_t", "Mutex.", []], ["pid_t", "Kiểu pid.", []],
  ["ssize_t", "size_t có dấu (trả về -1 khi lỗi).", []], ["size_t", "Kiểu kích thước không dấu.", []], ["FILE", "Luồng file của stdio.", []],
].map(([name, doc, fields]) => ({ kind: "type", name, doc, sig: name, fields }));

const FIELDS = [...new Set(TYPES.flatMap((t) => t.fields))];

const KEYWORDS = ["if", "else", "for", "while", "do", "switch", "case", "default", "break", "continue", "return", "sizeof", "struct", "typedef", "enum", "const", "static", "void", "int", "char", "long", "unsigned", "double", "float", "short"];

const INCLUDES = [...new Set(FN.map((f) => f.header))].sort();

// Snippet: [nhãn, mô tả, nội dung (cú pháp snippet của Monaco)]
const SNIPPETS = [
  ["main", "Hàm main", "int main(int argc, char *argv[]) {\n\t$0\n\treturn 0;\n}"],
  ["for", "Vòng for đếm", "for (int ${1:i} = 0; ${1:i} < ${2:n}; ${1:i}++) {\n\t$0\n}"],
  ["while", "Vòng while", "while (${1:cond}) {\n\t$0\n}"],
  ["if", "Rẽ nhánh if", "if (${1:cond}) {\n\t$0\n}"],
  ["ifelse", "Rẽ nhánh if / else", "if (${1:cond}) {\n\t$2\n} else {\n\t$0\n}"],
  ["switch", "Lệnh switch", "switch (${1:x}) {\n\tcase ${2:0}:\n\t\t$0\n\t\tbreak;\n\tdefault:\n\t\tbreak;\n}"],
  ["sockaddr", "Khai báo và điền struct sockaddr_in", "struct sockaddr_in ${1:addr};\nmemset(&${1:addr}, 0, sizeof(${1:addr}));\n${1:addr}.sin_family = AF_INET;\n${1:addr}.sin_port = htons(${2:8080});\n${1:addr}.sin_addr.s_addr = ${3:htonl(INADDR_ANY)};"],
  ["tcpserver", "Khung server TCP: socket, bind, listen", "int ${1:listenfd} = socket(AF_INET, SOCK_STREAM, 0);\nif (${1:listenfd} < 0) { perror(\"socket\"); exit(1); }\nint on = 1;\nsetsockopt(${1:listenfd}, SOL_SOCKET, SO_REUSEADDR, &on, sizeof(on));\n\nstruct sockaddr_in addr;\nmemset(&addr, 0, sizeof(addr));\naddr.sin_family = AF_INET;\naddr.sin_port = htons(${2:8080});\naddr.sin_addr.s_addr = htonl(INADDR_ANY);\nif (bind(${1:listenfd}, (struct sockaddr *)&addr, sizeof(addr)) < 0) { perror(\"bind\"); exit(1); }\nif (listen(${1:listenfd}, 5) < 0) { perror(\"listen\"); exit(1); }\n$0"],
  ["acceptloop", "Vòng lặp accept (server tuần tự)", "while (1) {\n\tstruct sockaddr_in client;\n\tsocklen_t len = sizeof(client);\n\tint ${1:connfd} = accept(${2:listenfd}, (struct sockaddr *)&client, &len);\n\tif (${1:connfd} < 0) { perror(\"accept\"); continue; }\n\t$0\n\tclose(${1:connfd});\n}"],
  ["tcpclient", "Khung client TCP: socket, connect", "int ${1:sockfd} = socket(AF_INET, SOCK_STREAM, 0);\nif (${1:sockfd} < 0) { perror(\"socket\"); exit(1); }\n\nstruct sockaddr_in server;\nmemset(&server, 0, sizeof(server));\nserver.sin_family = AF_INET;\nserver.sin_port = htons(${2:8080});\nserver.sin_addr.s_addr = inet_addr(\"${3:127.0.0.1}\");\nif (connect(${1:sockfd}, (struct sockaddr *)&server, sizeof(server)) < 0) { perror(\"connect\"); exit(1); }\n$0"],
  ["udpserver", "Khung server UDP: socket, bind", "int ${1:sockfd} = socket(AF_INET, SOCK_DGRAM, 0);\nif (${1:sockfd} < 0) { perror(\"socket\"); exit(1); }\n\nstruct sockaddr_in addr;\nmemset(&addr, 0, sizeof(addr));\naddr.sin_family = AF_INET;\naddr.sin_port = htons(${2:8080});\naddr.sin_addr.s_addr = htonl(INADDR_ANY);\nif (bind(${1:sockfd}, (struct sockaddr *)&addr, sizeof(addr)) < 0) { perror(\"bind\"); exit(1); }\n$0"],
  ["udploop", "Vòng lặp recvfrom / sendto", "while (1) {\n\tchar buf[1024];\n\tstruct sockaddr_in client;\n\tsocklen_t len = sizeof(client);\n\tssize_t n = recvfrom(${1:sockfd}, buf, sizeof(buf) - 1, 0, (struct sockaddr *)&client, &len);\n\tif (n < 0) { perror(\"recvfrom\"); continue; }\n\tbuf[n] = '\\0';\n\t$0\n\tsendto(${1:sockfd}, buf, n, 0, (struct sockaddr *)&client, len);\n}"],
  ["recvloop", "Đọc dữ liệu tới khi đối phương đóng", "char buf[1024];\nssize_t n;\nwhile ((n = recv(${1:fd}, buf, sizeof(buf) - 1, 0)) > 0) {\n\tbuf[n] = '\\0';\n\t$0\n}"],
  ["readfile", "Đọc tệp bằng open/read rồi gửi từng khối", "char buf[4096];\nint ${1:fd} = open(${2:path}, O_RDONLY);\nif (${1:fd} != -1) {\n\tint n;\n\twhile ((n = read(${1:fd}, buf, sizeof(buf))) > 0) {\n\t\t$0\n\t}\n\tclose(${1:fd});\n}"],
  ["appendfile", "Mở tệp ghi nối tiếp bằng open (O_APPEND)", "int ${1:fd} = open(${2:path}, O_WRONLY | O_CREAT | O_APPEND, 0644);\nif (${1:fd} != -1) {\n\twrite(${1:fd}, ${3:buf}, ${4:n});\n\tclose(${1:fd});\n}$0"],
  ["freadfile", "Đọc tệp bằng fopen/fread rồi gửi từng khối", "char buf[4096];\nFILE *${1:f} = fopen(${2:path}, \"rb\");\nif (${1:f} != NULL) {\n\tsize_t n;\n\twhile ((n = fread(buf, 1, sizeof(buf), ${1:f})) > 0) {\n\t\t$0\n\t}\n\tfclose(${1:f});\n}"],
  ["fappendfile", "Mở tệp ghi nối tiếp bằng fopen (\"ab\")", "FILE *${1:f} = fopen(${2:path}, \"ab\");\nif (${1:f} != NULL) {\n\tfwrite(${3:buf}, 1, ${4:n}, ${1:f});\n\tfclose(${1:f});\n}$0"],
  ["selectloop", "Vòng lặp select cho nhiều client", "fd_set master, readfds;\nFD_ZERO(&master);\nFD_SET(${1:listenfd}, &master);\nint maxfd = ${1:listenfd};\nwhile (1) {\n\treadfds = master;\n\tif (select(maxfd + 1, &readfds, NULL, NULL, NULL) < 0) { perror(\"select\"); break; }\n\tfor (int fd = 0; fd <= maxfd; fd++) {\n\t\tif (!FD_ISSET(fd, &readfds)) continue;\n\t\tif (fd == ${1:listenfd}) {\n\t\t\tint c = accept(${1:listenfd}, NULL, NULL);\n\t\t\tif (c >= 0) { FD_SET(c, &master); if (c > maxfd) maxfd = c; }\n\t\t} else {\n\t\t\tchar buf[1024];\n\t\t\tssize_t n = recv(fd, buf, sizeof(buf), 0);\n\t\t\tif (n <= 0) { close(fd); FD_CLR(fd, &master); }\n\t\t\telse { $0 }\n\t\t}\n\t}\n}"],
  ["forkserver", "Mỗi client một tiến trình con (fork)", "signal(SIGCHLD, ${1:sigchld_handler});\nwhile (1) {\n\tint c = accept(${2:listenfd}, NULL, NULL);\n\tif (c < 0) continue;\n\tpid_t pid = fork();\n\tif (pid == 0) {\n\t\tclose(${2:listenfd});\n\t\t$0\n\t\tclose(c);\n\t\texit(0);\n\t}\n\tclose(c);\n}"],
  ["sigchld", "Handler thu hồi tiến trình con", "void ${1:sigchld_handler}(int sig) {\n\twhile (waitpid(-1, NULL, WNOHANG) > 0) {}\n}"],
  ["threadserver", "Mỗi client một thread (pthread)", "while (1) {\n\tint *c = malloc(sizeof(int));\n\t*c = accept(${1:listenfd}, NULL, NULL);\n\tif (*c < 0) { free(c); continue; }\n\tpthread_t tid;\n\tpthread_create(&tid, NULL, ${2:client_thread}, c);\n\tpthread_detach(tid);\n}"],
  ["threadfn", "Hàm chạy trong thread", "void *${1:client_thread}(void *arg) {\n\tint fd = *(int *)arg;\n\tfree(arg);\n\t$0\n\tclose(fd);\n\treturn NULL;\n}"],
  ["inc_all", "Các #include cho lập trình socket", "#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include <unistd.h>\n#include <sys/socket.h>\n#include <netinet/in.h>\n#include <arpa/inet.h>\n"],
];

/* ---------- tra cứu (toolkit + hàm do người dùng tự viết) ---------- */

const BY_NAME = new Map([...FN, ...MACROS, ...CONSTS, ...TYPES].map((e) => [e.name, e]));

const DEF_FN = /^[ \t]*(?:static[ \t]+|inline[ \t]+)*([A-Za-z_][\w \t\*]*?[ \t\*])([A-Za-z_]\w*)[ \t]*\(([^;{)]*)\)[ \t]*(?:\{|$)/gm;
const DEF_MACRO = /^[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)(?:\(([^)]*)\))?[ \t]*(.*)$/gm;
const DEF_TYPE = /^[ \t]*(?:typedef[ \t]+)?struct[ \t]+([A-Za-z_]\w*)[ \t]*\{/gm;
const NOT_FN = new Set(["if", "for", "while", "switch", "return", "sizeof", "else", "do"]);

// Quét model để lấy hàm / macro / struct do người dùng định nghĩa (kèm vị trí để đi tới định nghĩa).
function userSymbols(model) {
  const text = model.getValue(), code = mask(text), out = [];
  let m;
  DEF_FN.lastIndex = 0;
  while ((m = DEF_FN.exec(code))) { // dò trên bản đã xoá chú thích để không nhận hàm nằm trong comment
    const name = m[2];
    if (NOT_FN.has(name)) continue;
    const ret = m[1].trim(), params = m[3].trim() || "void";
    out.push({ kind: "fn", name, ret, params, doc: "Hàm bạn tự định nghĩa.", sig: `${ret} ${name}(${params})`, args: params === "void" ? [] : params.split(/,\s*/), offset: m.index + m[0].indexOf(name), user: true });
  }
  DEF_MACRO.lastIndex = 0;
  while ((m = DEF_MACRO.exec(text))) {
    const name = m[1];
    out.push({ kind: m[2] != null ? "fn" : "const", name, params: m[2] ?? "", doc: m[3] ? `#define → \`${m[3].trim()}\`` : "Macro bạn tự định nghĩa.", sig: m[2] != null ? `${name}(${m[2]})` : name, args: m[2] ? m[2].split(/,\s*/) : [], offset: m.index + m[0].indexOf(name), user: true });
  }
  DEF_TYPE.lastIndex = 0;
  while ((m = DEF_TYPE.exec(code))) out.push({ kind: "type", name: m[1], doc: "Struct bạn tự định nghĩa.", sig: `struct ${m[1]}`, fields: [], offset: m.index + m[0].indexOf(m[1]), user: true });
  return out;
}

const lookup = (model, name) => userSymbols(model).find((s) => s.name === name) || BY_NAME.get(name);

/* ---------- đọc ngữ cảnh gọi hàm (cho signature help) ---------- */

// Xoá chú thích / chuỗi / ký tự nhưng giữ nguyên độ dài để chỉ số vị trí không lệch.
function mask(src) {
  return src.replace(/\/\*[\s\S]*?(?:\*\/|$)|\/\/[^\n]*|"(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?/g, (s) => s.replace(/[^\n]/g, " "));
}

// Con trỏ đang nằm trong chú thích, chuỗi hoặc ký tự? (xét ký tự ngay trước con trỏ)
function inNonCode(model, pos) {
  const end = model.getOffsetAt(pos);
  if (end === 0) return false;
  const raw = model.getValue().slice(0, end);
  const c = raw[end - 1];
  return !/\s/.test(c) && /\s/.test(mask(raw)[end - 1]);
}

function callAt(model, pos) {
  const text = mask(model.getValue());
  const end = model.getOffsetAt(pos);
  let depth = 0, commas = 0;
  for (let i = end - 1; i >= 0; i--) {
    const c = text[i];
    if (c === ")" || c === "]" || c === "}") depth++;
    else if (c === "(" || c === "[" || c === "{") {
      if (depth === 0) {
        if (c !== "(") return null;
        const name = /([A-Za-z_]\w*)\s*$/.exec(text.slice(0, i));
        return name ? { name: name[1], index: commas } : null;
      }
      depth--;
    } else if (c === "," && depth === 0) commas++;
    else if (c === ";" && depth === 0) return null;
  }
  return null;
}

/* ---------- kiểm tra ngoặc ---------- */

function bracketMarkers(monaco, model) {
  const text = mask(model.getValue()), stack = [], out = [];
  const pairs = { ")": "(", "]": "[", "}": "{" };
  const mk = (i, msg) => {
    const a = model.getPositionAt(i), b = model.getPositionAt(i + 1);
    out.push({ severity: monaco.MarkerSeverity.Error, message: msg, startLineNumber: a.lineNumber, startColumn: a.column, endLineNumber: b.lineNumber, endColumn: b.column });
  };
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if ("([{".includes(c)) stack.push([c, i]);
    else if (pairs[c]) {
      const top = stack.pop();
      if (!top) mk(i, `Thừa '${c}' — không có ngoặc mở tương ứng`);
      else if (top[0] !== pairs[c]) { mk(top[1], `Ngoặc '${top[0]}' không khớp với '${c}'`); mk(i, `'${c}' không khớp với '${top[0]}'`); }
    }
  }
  for (const [c, i] of stack) mk(i, `Thiếu ngoặc đóng cho '${c}'`);
  return out.slice(0, 20);
}

/* ---------- đăng ký với Monaco ---------- */

const md = (s) => ({ value: s });
const sigDoc = (e) => "```c\n" + e.sig + "\n```\n" + e.doc + (e.header ? `\n\n\`#include <${e.header}>\`` : "");

// Giá trị mặc định cho các tuỳ chọn gợi ý (dùng chung với Cài đặt).
export const C_ASSIST_DEFAULTS = {
  acAuto: true,        // tự hiện danh sách gợi ý khi gõ
  acTrigger: true,     // hiện gợi ý khi gõ ký tự kích hoạt (. -> ...)
  acEnter: true,       // Enter chấp nhận gợi ý (tắt thì chỉ Tab)
  acWords: true,       // gợi ý theo từ đã xuất hiện trong file
  acFunctions: true,   // hàm, hằng, kiểu của bộ công cụ socket/process/thread
  acSnippets: true,    // khung code (snippet)
  sigHelp: true,       // gợi ý tham số khi gõ "("
  hover: true,         // tài liệu khi trỏ chuột vào hàm
  goToDef: true,       // F12 / Ctrl+click tới định nghĩa trong file
  lint: true,          // báo ngoặc thiếu / thừa
  autoClose: true,     // tự đóng ngoặc, nháy
};

let cfgGetter = () => ({}); // provider luôn đọc cấu hình của editor mới nhất
// Provider của Monaco là toàn cục. Khi Next nạp lại module (HMR) hoặc mở lại editor, bản cũ phải được gỡ,
// nếu không các provider cũ vẫn chạy song song và gây lỗi cũ dù code đã sửa. Giữ danh sách trên globalThis để sống qua HMR.
const KEEP = "__cAssistProviders";

// Trả về { refresh(): chạy lại kiểm tra lỗi, dispose() } cho một editor.
export function setupCAssist(monaco, editor, getCfg) {
  cfgGetter = getCfg;
  for (const d of globalThis[KEEP] || []) { try { d.dispose(); } catch {} }
  const reg = (globalThis[KEEP] = []);
  {
    const L = "c";
    const on = (k) => cfgGetter()?.[k] !== false;

    reg.push(monaco.languages.registerCompletionItemProvider(L, {
      triggerCharacters: [".", ">"], // '.' và '->' để gợi ý trường struct
      provideCompletionItems(model, position, context) {
        const K = monaco.languages.CompletionItemKind, Ins = monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet;
        const line = model.getLineContent(position.lineNumber);
        const upto = line.slice(0, position.column - 1);
        const w = model.getWordUntilPosition(position);
        const range = { startLineNumber: position.lineNumber, endLineNumber: position.lineNumber, startColumn: w.startColumn, endColumn: w.endColumn };
        const none = { suggestions: [] };
        const byTrigger = context?.triggerKind === monaco.languages.CompletionTriggerKind.TriggerCharacter;
        const suggestions = [];

        if (inNonCode(model, position)) return none; // trong chú thích / chuỗi / ký tự

        // Dòng #include: chỉ gợi ý tên header, và không làm gì sau khi đã đóng '>'.
        const inc = /^\s*#\s*include\s*(<[^>]*)?$/.exec(upto);
        if (/^\s*#\s*include(?![A-Za-z_])/.test(upto)) {
          if (!inc || byTrigger || !on("acFunctions")) return none;
          const lt = upto.indexOf("<");
          if (lt < 0) return none;
          const r = { ...range, startColumn: lt + 2 }; // thay cả "sys/so" chứ không chỉ "so"
          for (const h of INCLUDES) suggestions.push({ label: h, kind: K.File, insertText: `${h}>`, range: r, detail: `#include <${h}>` });
          return { suggestions };
        }

        // Sau '.' hoặc '->' chỉ gợi ý trường struct.
        if (/(?:\.|->)\s*\w*$/.test(upto)) {
          if (on("acFunctions")) for (const f of FIELDS) suggestions.push({ label: f, kind: K.Field, insertText: f, range, detail: "trường struct" });
          return { suggestions };
        }
        // Ký tự kích hoạt không dẫn tới '.'/'->' (ví dụ '>' của "a > b") thì không hiện gì, kẻo Enter chọn nhầm.
        if (byTrigger) return none;
        // Chưa gõ chữ nào mà không phải do bấm Ctrl+Space thì cũng không hiện (sau ; ) } ...).
        if (!w.word && context?.triggerKind !== monaco.languages.CompletionTriggerKind.Invoke) return none;

        const known = new Set();
        if (on("acFunctions")) {
          for (const e of [...userSymbols(model), ...FN, ...MACROS, ...CONSTS, ...TYPES]) {
            if (known.has(e.name)) continue;
            known.add(e.name);
            const base = { label: e.name, range, documentation: md(sigDoc(e)), detail: e.sig };
            if (e.kind === "fn") {
              const ph = e.args.map((a, i) => `\${${i + 1}:${(/([A-Za-z_]\w*)\W*$/.exec(a) || [, a])[1]}}`).join(", ");
              suggestions.push({ ...base, kind: K.Function, insertText: e.args.length ? `${e.name}(${ph})$0` : `${e.name}()$0`, insertTextRules: Ins, sortText: "1" + e.name });
            } else if (e.kind === "const") suggestions.push({ ...base, kind: K.Constant, insertText: e.name, sortText: "2" + e.name });
            else suggestions.push({ ...base, kind: K.Struct, insertText: e.name, sortText: "2" + e.name });
          }
        }
        // Snippet xếp sau hàm/hằng khi điểm khớp bằng nhau: gõ "sock" phải ra socket trước, không phải khung code.
        const snipNames = new Set(on("acSnippets") ? SNIPPETS.map((x) => x[0]) : []);
        if (on("acSnippets")) {
          for (const [label, detail, body] of SNIPPETS)
            suggestions.push({ label, kind: K.Snippet, detail, documentation: md("```c\n" + body.replace(/\$\{\d+:([^}]*)\}/g, "$1").replace(/\$0/g, "") + "\n```"), insertText: body, insertTextRules: Ins, range, sortText: "3" + label });
        }
        if (on("acFunctions")) for (const k of KEYWORDS) if (!snipNames.has(k)) suggestions.push({ label: k, kind: K.Keyword, insertText: k, range, sortText: "4" + k });

        // Danh sách của mình đã có thì Monaco bỏ gợi ý theo từ, nên tự thêm tên biến/hàm trong file.
        if (on("acWords")) {
          const taken = new Set([...known, ...KEYWORDS, ...snipNames]);
          const src = mask(model.getValue()).replace(/^[ \t]*#[ \t]*include.*$/gm, (x) => " ".repeat(x.length)); // giữ nguyên độ dài để vị trí không lệch
          const cursorOff = model.getOffsetAt(position) - w.word.length;
          for (const m of src.matchAll(/[A-Za-z_]\w{2,}/g)) {
            if (taken.has(m[0]) || m.index === cursorOff) continue; // bỏ chính từ đang gõ
            taken.add(m[0]);
            suggestions.push({ label: m[0], kind: K.Text, insertText: m[0], range, sortText: "5" + m[0] });
          }
        }
        return { suggestions };
      },
    }));

    reg.push(monaco.languages.registerSignatureHelpProvider(L, {
      signatureHelpTriggerCharacters: ["(", ","],
      signatureHelpRetriggerCharacters: [","],
      provideSignatureHelp(model, position) {
        if (!on("sigHelp")) return null;
        const call = callAt(model, position);
        const e = call && lookup(model, call.name);
        if (!e || e.kind !== "fn") return null;
        const params = e.args.map((a) => ({ label: a }));
        const idx = Math.min(call.index, Math.max(params.length - 1, 0));
        return { value: { signatures: [{ label: e.sig, documentation: md(e.doc), parameters: params }], activeSignature: 0, activeParameter: idx }, dispose() {} };
      },
    }));

    reg.push(monaco.languages.registerHoverProvider(L, {
      provideHover(model, position) {
        if (!on("hover") || inNonCode(model, position)) return null;
        const w = model.getWordAtPosition(position);
        const e = w && lookup(model, w.word);
        if (!e) return null;
        return { range: new monaco.Range(position.lineNumber, w.startColumn, position.lineNumber, w.endColumn), contents: [md(sigDoc(e))] };
      },
    }));

    reg.push(monaco.languages.registerDefinitionProvider(L, {
      provideDefinition(model, position) {
        if (!on("goToDef")) return null;
        const w = model.getWordAtPosition(position);
        if (!w) return null;
        return userSymbols(model).filter((s) => s.name === w.word).map((s) => {
          const p = model.getPositionAt(s.offset);
          return { uri: model.uri, range: new monaco.Range(p.lineNumber, p.column, p.lineNumber, p.column + s.name.length) };
        });
      },
    }));
  }

  let timer = 0;
  const run = () => {
    const model = editor.getModel();
    if (!model) return;
    monaco.editor.setModelMarkers(model, "c-assist", getCfg()?.lint === false ? [] : bracketMarkers(monaco, model));
  };
  const sub = editor.onDidChangeModelContent(() => { clearTimeout(timer); timer = setTimeout(run, 400); });
  run();
  return { refresh: run, dispose() { clearTimeout(timer); sub.dispose(); } };
}

// Tuỳ chọn Monaco tương ứng với cài đặt (gộp vào prop options của editor).
export function cAssistOptions(s) {
  const v = (k) => (s[k] === undefined ? C_ASSIST_DEFAULTS[k] : s[k]);
  return {
    quickSuggestions: v("acAuto") ? { other: true, comments: false, strings: false } : false,
    suggestOnTriggerCharacters: v("acTrigger"),
    acceptSuggestionOnEnter: v("acEnter") ? "on" : "off",
    wordBasedSuggestions: v("acWords") ? "currentDocument" : "off",
    snippetSuggestions: "top",
    parameterHints: { enabled: v("sigHelp"), cycle: true },
    autoClosingBrackets: v("autoClose") ? "languageDefined" : "never",
    autoClosingQuotes: v("autoClose") ? "languageDefined" : "never",
    definitionLinkOpensInPeek: false,
  };
}
