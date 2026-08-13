# ĐẶC TẢ KỸ THUẬT VÀ KIẾN TRÚC HÌNH THỨC NGÔN NGỮ LẬP TRÌNH .KO(FORMAL TECHNICAL SPECIFICATION & ARCHITECTURAL MANUAL FOR .KO)
Phiên bản đặc tả (Specification Version): 2.601 - External Package Management & Automated Ingestion Extension
Phân loại ngôn ngữ: Đa mô hình (Multi-Paradigm: Imperative, Object-Oriented, Low-Level Memory Direct Manipulation, Structural Sequential Upward Exception Handling)
**LỜI NÓI ĐẦU: CÁCH ĐỌC TÀI LIỆU NÀY (FOR ALL READERS)
Tài liệu này được trình bày theo định dạng Mục tiêu Kép (Dual-Layer Standard):Lớp Toán Học & Kỹ Thuật (Mathematical & CS Formalism): Dành cho các kỹ sư compiler, chuyên gia hệ thống để xây dựng Trình biên dịch chuẩn xác.Lớp Giải Thích Trực Quan (Intuitive Conceptual Layer): Sử dụng các mô hình ẩn dụ đời sống, giúp người mới học hoặc không có nền tảng chuyên sâu cũng nắm bắt ngay lập tức nguyên lý hoạt động**.
# I. KIẾN TRÚC HẠT NHÂN VÀ THỰC THI CHUẨN HOÁ (RUNTIME ARCHITECTURE & ENGINE TARGET MAPPING)
Ngôn ngữ .ko vận hành dựa trên mô hình thực thi lai (Hybrid Execution Target Engine).Trình biên dịch/phiên dịch trung tâm (compiler.py) đóng vai trò như một "Nhạc trưởng". Nó nhận mã nguồn, phân tích cú pháp và phân chia công việc cho các "Nhà thầu chuyên biệt" ở bên dưới thực thi.
## 1. Mô hình Toán học Pipeline và Sơ đồ Thực thiMô hình chuyển đổi trạng thái thực thi được định nghĩa toán học thông qua hàm ánh xạ pipeline:
$$\mathcal{P}: \text{SourceCode}_{.ko} \xrightarrow{\text{Lexer/Parser}} \text{AST} \xrightarrow{\text{ScopeResolver}} \text{EngineTarget} \xrightarrow{\text{Execution}} \text{State}'$$
+-------------------------------------------------------------------+
|                     Mã Nguồn Cấp Cao (.ko)                        |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|        Bộ Phân Tích Cú Pháp Trừu Tượng (Trình điều phối compiler.py)|
+-------------------------------------------------------------------+
                  /                                   \
                 /                                     \
                v                                       v
+--------------------------+           +----------------------------+
|   Subsystem Import Engine|           |    Subsystem Loop Engine   |
|      (Import.java)       |           |         (Loop.cpp)         |
+--------------------------+           +----------------------------+
| - Dynamic Path Resolution|           | - Low-level Loop Unrolling |
| - Scope Table Ingestion  |           | - Cache Line Optimization  |
| - Module Signature Check |           | - CPU Counter Registers    |
+--------------------------+           +----------------------------+

2. Ánh xạ Từ khóa Đặc biệt sang Tệp Thực thi Hệ thống (Special Keyword Native Mapping)A. Thư viện Nạp Module: Import Subsystem TargetChỉ thị ngôn ngữ: ImportTệp mã nguồn chịu trách nhiệm bên dưới: Import.javaGiải thích đơn giản (Intuitive Analogy): Coi Import.java như một "Thủ thư". Khi bạn dùng từ khóa Import hoặc lệnh cài đặt thư viện, thủ thư Java sẽ đi tìm gói thư viện, kiểm tra tính hợp lệ, biên dịch và mang đặt lên bàn làm việc của bạn để bạn sẵn sàng sử dụng.Ngữ nghĩa toán học & kỹ thuật:$$\text{Import}_{\text{subsystem}}: \text{ModuleName} \times \text{ScopeTag} \to \mathcal{S}_{\text{updated\_scope\_table}}$$Phân giải đường dẫn tập tin (Dynamic Path Resolution).Xác thực chữ ký mã nguồn (Module Signature Verification).Tải lớp động (Dynamic Classloading) và chèn danh sách định danh vào Bảng Tầm Vực (Scope Table).B. Động cơ Vòng lặp Hiệu năng cao: Loop Subsystem TargetChỉ thị ngôn ngữ: LoopTệp mã nguồn chịu trách nhiệm bên dưới: Loop.cppGiải thích đơn giản (Intuitive Analogy): Coi Loop.cpp như một "Tay đua F1". Việc lặp lại một hành động hàng triệu lần có thể làm chậm chương trình. Khi dùng từ khóa Loop, công việc lặp sẽ được chuyển giao cho mã C++ chạy trực tiếp ở cấp phần cứng CPU với tốc độ tối đa.Ngữ nghĩa toán học & kỹ thuật:$$\text{Loop}_{\text{subsystem}}: \text{IterCondition} \times \text{BodyBlock} \xrightarrow{\text{Native C++}} \Delta \text{State}$$Ép kiểu và tối ưu hóa thanh ghi cứng CPU (Hardware Register Allocation).Bỏ qua các overhead của bộ phiên dịch, tối ưu bộ đệm lệnh (Instruction Cache Line Optimization).II. MÔ HÌNH LÝ THUYẾT VÀ TỪ VỰNG CÚ PHÁP TỔNG QUÁT (LEXICAL & FORMAL SYNTAX GRAMMAR)1. Nguyên tắc Tách biệt Lệnh và Dữ liệu (Code vs. Data Separation Principle)Ngôn ngữ .ko thiết lập ranh giới phân định tuyệt đối giữa Khối lệnh thực thi (Executable Control Block) và Cấu trúc dữ liệu/Tham số (Data Container).Không gian Lệnh / Scope Block ($\mathcal{B}_E$): Sử dụng duy nhất cặp ngoặc vuông [ ]. (Nơi chứa các hành động, câu lệnh, khối code).Không gian Dữ liệu & Tham số ($\mathcal{D}_P$): Sử dụng cặp ngoặc tròn ( ) cho tập hợp/tham số và ngoặc nhọn { } cho ánh xạ Key-Value.Tiên đề Tiên quyết (Delimiter Axiom):$$\mathcal{B}_E \cap \mathcal{D}_P = \emptyset$$(Ý nghĩa: Dấu ngoặc vuông [ ] KHÔNG ĐƯỢC chứa dữ liệu thuần túy, và ngoặc tròn ( ) KHÔNG ĐƯỢC chứa các khối lệnh điều khiển).2. Ký hiệu Nhận dạng Đặc biệt (Sigils & Delimiters Semantics)Ký hiệu / SigilTên gọi chuẩn học thuậtÝ nghĩa & Cách dùng đơn giảnVí dụ minh họa~Toán tử Định danh (Identifier Sigil)Dấu "đánh dấu" đứng trước tên biến, tên hàm, tên lớp khi khai báo hoặc khi gọi.int(10)~age  ~Hero~p1  ~my_func()< >Thẻ Hệ thống (System Tag Delimiters)Dùng để bao bọc các lệnh có sẵn của hệ thống như in ấn, nhập dữ liệu, đo độ dài, giải phóng bộ nhớ, mã hóa hex/ASCII...<printf>  <input>  <len>  <memory>  <encode>$Con trỏ Tham chiếu Thể hiện (Instance Pointer)Dùng để "chỉ tới" thuộc tính hoặc phương thức bên trong một Lớp (Class) hay Module.$p1~take_damage()"\n"Toán tử Ngắt Dòng (Newline Sequence)Ký tự xuống dòng, bắt buộc phải nằm trong dấu ngoặc kép "\n".<printf>^("Hello\n")  <print>string^(x"\n")``Dấu Phân Cách Ghi Chú (Comment Delimiters)3. Cú pháp Hình thức EBNF (Extended Backus-Naur Form)Program            ::= ModuleImport* Statement* MainBlock ExceptionHandler* ;
MainBlock          ::= "[" Statement* ExceptionHandler* "]" ;
Statement          ::= VarDecl | Assignment | FuncDecl | ClassDecl | ControlFlow | MemoryOp | EncodingOp | LenOp | ExceptionHandler ;

Sigil              ::= "~" ;
SystemTagOpen      ::= "<" ;
SystemTagClose     ::= ">" ;
Comment            ::= "|" [^|]* "|" ;
NewlineEscape      ::= '"\n"' ;

Identifier         ::= [a-zA-Z_][a-zA-Z0-9_]* ;
VarDecl            ::= PrimitiveType "(" Expression ")" Sigil Identifier ;
PrimitiveType      ::= "int" | "freal" | "string" | "booling" | "byte" | "bytes" ;
EncodingOp         ::= SystemTagOpen "encode(" EncodingType ")" SystemTagClose "^(" Expression ")" ;
EncodingType       ::= "`ASCII`" | "`UTF-8`" | "`UTF-16`" ;
LenOp              ::= SystemTagOpen "len" SystemTagClose "^(" Expression ")" ;

4. Hệ thống Toán tử (Operators Domain)Toán tử Số học ($\mathbb{O}_{arith}$):+ : Phép cộng ($a + b$)- : Phép trừ ($a - b$)* : Phép nhân ($a \times b$)/ : Phép chia ($a \div b$)% : Phép chia lấy số dư ($a \pmod b$)Toán tử Logic ($\mathbb{O}_{logic}$):&& : Phép VÀ logic (Logical AND - Đúng khi cả 2 cùng đúng)%% : Phép HOẶC logic (Logical OR - Đúng khi 1 trong 2 đúng)5. Tiên đề Tầm vực Thực thi Toàn cục (Global Scope Execution Constraint Axiom)Tiên đề: Các câu lệnh thực thi (ví dụ: phép tính, lệnh in <printf>) không được nằm tự do bên ngoài toàn cục. Chúng bắt buộc phải nằm bên trong một Hàm hoặc nằm trong Khối Thực thi Chính [ ]. Phạm vi toàn cục bên ngoài chỉ chấp nhận: Lệnh Import, Khai báo Hàm, và Khai báo Lớp.III. HỆ THỐNG KIỂU DỮ LIỆU NGUYÊN THỦY VÀ CẤU TRÚC PHỨC HỢP1. Kiểu Dữ liệu Nguyên thủy & Vùng Đệm Byte (Primitive Data Domains & Byte Buffers)Công thức khai báo tổng quát:$$\text{KiểuDữLiệu}(\text{GiáTrịBanĐầu}) \sim \text{TênBiến}$$Kiểu dữ liệuMiền giá trị Toán học (D)Ý nghĩa thực tế & Mô tảVí dụ Cú pháp Chuẩnint$\mathbb{Z} \cap [-2^{63}, 2^{63}-1]$Số nguyên (không có dấu phẩy)int(100)~hpfreal$\mathbb{R} \approx \text{Double Precision}$Số thực (có dấu thập phân)freal(3.14159)~pistringChuỗi ký tự UTF-8 ($\Sigma^*$)Văn bản / Dòng chữstring("Phong\n")~namebooling$\mathbb{B} = \{\mathtt{\backslash True\backslash}, \mathtt{\backslash False\backslash}\}$Giá trị đúng/saibooling(\True\)~is_activebyte$\mathbb{B} \in \{0, 1\}^n$Biểu diễn Nhị phân (Binary Values): Tự động chuyển đổi dữ liệu truyền vào (ký tự, số) thành dạng nhị phân 0 và 1.byte("A")~b_valbytes$\mathcal{H} \in \{0x00 \dots 0xFF\}^*$Vùng đệm Hex (Hexadecimal Buffer): Cấp phát vùng nhớ trống biểu diễn qua mã Hex, hoặc tạo từ chuỗi Hex thô.bytes(16)~empty_buf2. Cấu trúc Dữ liệu Phức hợp (Complex Data Structures)Tuple / Mảng số: (1, 2)~aMảng Chuỗi: ('a', 'b')~bDanh sách Lồng nhau (Nested List): (1('a', 'b'))~listTừ điển (Dictionary Key-Value): (1{'a'})~dic3. Cú pháp Truy xuất Chỉ mục (Indexing Operator Semantics)Mọi thao tác lấy dữ liệu từ mảng/từ điển bắt buộc phải bọc chỉ mục trong Thẻ Hệ thống < >:Lấy phần tử đơn (Chỉ số từ 0): list<0> $\implies$ Lấy phần tử đầu tiên.Lấy phần tử lồng nhau: list<1<0>> $\implies$ Lấy phần tử thứ 0 nằm trong danh sách con ở vị trí thứ 1.Lấy theo Key của Từ điển: dic{1{'a'}}IV. HỆ THỐNG NHẬP/XUẤT, BỘ NHỚ, MÃ HÓA, ĐO ĐỘ DÀI VÀ ĐỘT BIẾN TRẠNG THÁI1. Cấu trúc Xuất Dữ liệu (Output Stream Directives)Toàn bộ chỉ thị xuất màn hình hỗ trợ chèn chuỗi escape "\n" để xuống dòng.Xuất Văn bản Tĩnh:<print>string^("Xin chao\n")
<print>string^(x"\n")

Xuất Chuỗi Định dạng Biến (String Interpolation):<printf>^("Player HP: {hp}\n")

2. Thẻ Hệ thống Mã hóa Dữ liệu (<encode>)Thẻ hệ thống <encode> chuyển đổi chuỗi hoặc dữ liệu văn bản sang mảng byte được mã hóa theo các chuẩn giao tiếp tiêu chuẩn (ASCII, UTF-8, UTF-16).$$\text{\texttt{<encode(`Format`)>}}\text{\textasciicircum}(S) \implies \text{Encode string } S \text{ to byte array using } \text{Format}$$Cú pháp Mã hóa ASCII:<encode(`ASCII`)>^("Hello World\n")

Cú pháp Mã hóa UTF-8:<encode(`UTF-8`)>^("Xin chào .ko\n")

Lưu mã hóa vào biến bytes:bytes(<encode(`UTF-8`)>^("Dữ liệu bảo mật\n"))~encoded_data

3. Thẻ Hệ thống Đo Độ Dài Dữ liệu (<len>)Thẻ hệ thống <len> trả về kích thước/độ dài (số lượng phần tử, số byte, hoặc số ký tự) của một cấu trúc dữ liệu, chuỗi văn bản, hoặc vùng đệm bộ nhớ.$$\text{\texttt{<len>}}\text{\textasciicircum}(D) \implies \vert{}D\vert{} \in \mathbb{N}_0$$Đo độ dài chuỗi (string):int(<len>^("Xin chào .ko\n"))~str_length

Đo kích thước vùng đệm Hex / Byte (bytes / byte):bytes(32)~buffer
int(<len>^(buffer))~buf_size    | Trả về: 32 |

Đo số lượng phần tử trong Danh sách / Tuple / Từ điển:('Kiếm', 'Khiên', 'Bình máu')~inventory
int(<len>^(inventory))~item_count    | Trả về: 3 |

4. Cấu trúc Nhập Dữ liệu (<input>) - 3 Chế độ Vận hànhChế độ 1: In dòng nhắc thuần (không lưu vào biến):<input>("Nhập thông tin: \n")

Chế độ 2: Ghi đè vào biến đã có sẵn:string("")~x
<input>(x)  | Dữ liệu người dùng nhập sẽ ghi đè vào biến x |

Chế độ 3: Hứng dữ liệu thông qua toán tử &=:Tạo biến mới tại chỗ:<input>("Nhập tên: \n")&=string("")~name

Gán vào biến đã có:<input>("Nhập tên: \n")&=name

5. Thao tác Bộ nhớ Cấp thấp (<memory>)Để hiểu phần này, hãy tưởng tượng RAM máy tính như một "Dãy các ngăn kéo có đánh số địa chỉ".Truy xuất Địa chỉ Ô nhớ (Memory Address): Xem số nhà/địa chỉ của ngăn kéo đang chứa biến h:int(0)~h
<memory>^h  | Trả về địa chỉ ô nhớ, ví dụ: 0x7ffd56 |

Giải phóng Bộ nhớ Chủ động (<memory>dete): Xóa sạch dữ liệu trong ngăn kéo ngay lập tức để trả lại bộ nhớ cho máy tính:$$\mathcal{M}_{\text{free}}(h) \implies \text{Deallocate Memory Segment at } \&h$$<memory>dete(h)  | Ô nhớ chứa h lập tức giải phóng |

6. Đột biến Trạng thái Tức thì (<now>) - Immediate Mutation OperatorThẻ <now> giống như phép "dịch chuyển tức thời" giá trị mới vào ô nhớ của biến mà không cần thông qua biến trung gian.$$\langle \text{\texttt{<now>}}(e) > x, \, \sigma \rangle \to \sigma [x \mapsto \mathcal{E}\llbracket e \rrbracket \sigma]$$<now>(100)>hp          | Gán thẳng 100 vào hp |
<now>(hp - damage)>hp  | Cập nhật hp mới = hp cũ - damage |

V. CẤU TRÚC HÀM, GIÁ TRỊ TRẢ VỀ VÀ KHỐI THỰC THI CHÍNH1. Định nghĩa và Gọi Hàm (Function Definition & Invocation)Định nghĩa Hàm:tên_hàm(kiểu_1~tham_số_1, kiểu_2~tham_số_2) [
    | Khối các câu lệnh xử lý bên trong hàm |
]

Gọi Hàm:~tên_hàm(giá_trị_1, giá_trị_2)

2. Cơ chế Trả về Giá trị (<return>)Thẻ <return> ngắt ngay lập tức hàm và "gửi trả" một giá trị về cho nơi đã gọi nó.calculate_power(int~base) [
    <return>(base * 2)
]

| Hứng giá trị trả về khi tạo biến mới |
int(~calculate_power(10))~total

| Cập nhật giá trị trả về qua thẻ đột biến <now> |
<now>(~calculate_power(20))>total

3. Khối Thực thi Chính (Main Entry Point Block)Khối Main được ký hiệu duy nhất bởi cặp ngoặc vuông vô danh [ ].Mọi tệp .ko chạy độc lập bắt buộc phải có đúng 1 Khối Main.VI. CẤU TRÚC ĐIỀU KHIỂN LUỒNG (CONTROL FLOW)1. Rẽ nhánh Điều kiện (Conditional Branching)<if>(hp > 0 && is_active == \True\) [
    <printf>^("Nhân vật còn sống!\n")
]
<elif>(hp <= 0 %% is_active == \False\) [
    <printf>^("Nhân vật kiệt sức!\n")
]
<else> [
    <printf>^("Trạng thái không xác định!\n")
]

2. Hệ thống Vòng lặp (Loop Engine Target)Mọi vòng lặp bắt buộc phải có từ khóa Loop đứng trước để kích hoạt bộ xử lý siêu tốc Loop.cpp.A. Vòng lặp Đếm Số lần (<for>)Cú pháp: <for>(~biến_đếm=bắt_đầu(bước_nhảy)&=kết_thúc)Bước nhảy mặc định (+1):Loop <for>(~x=1&=5) [
    | x sẽ nhận lần lượt các giá trị: 1, 2, 3, 4, 5 |
]

Bước nhảy tùy chỉnh:Loop <for>(~x=1(2)&=5) [
    | x sẽ nhận lần lượt các giá trị: 1, 3, 5 |
]

B. Vòng lặp Điều kiện (while)@loop(hp > 0)
Loop <for.f.whle>@also [
    <printf>^("Đang chiến đấu...\n")
    <now>(hp - 10)>hp
]

VII. MÔ-ĐUN NẠP VÀ HỆ THỐNG PHẠM VI (MODULE IMPORT & SCOPE SYSTEM)1. Cú pháp Nạp Mô-đun (Xử lý bởi Import.java)$$\text{\textbf{Import}}(\$\text{ModuleName})\text{@also}\%\sim\text{Alias}!`\text{ScopeTag}`:\text{Alias}$$2. Quy định Thẻ Phạm vi Tầm vực (Scope Identifiers & Hierarchy)Thẻ phạm vi bắt buộc bọc trong dấu backtick `. Tầm vực vận hành theo mô hình "Vòng tròn lồng nhau": Phạm vi lớn hơn chứa phạm vi nhỏ hơn.$$\mathcal{S}_{\text{global}} \supset \mathcal{S}_{\text{main}} \supset \mathcal{S}_{\text{func}} \supset \mathcal{S}_{\text{class}}$$Thẻ ScopePhạm vi tác dụngGiải thích trực quan`global`Toàn cụcDùng được ở MỌI NƠI trong chương trình.`main` hoặc `a`Khối MainChỉ dùng được bên trong cặp ngoặc [ ] chính.`func`HàmDùng bên trong tất cả các Hàm.`class`LớpDùng bên trong tất cả các Lớp.`tên_hàm`Hàm cụ thểChỉ có tác dụng trong đúng hàm có tên đó.3. Thư viện Chuẩn Built-in System Modules| 1. Random Module |
Import($Random)@also%~random!`global`:random
int(<$random>(1, 100))~rand_val

| 2. OS Module |
Import($Os)@also%~os!`global`:os
<$os>("data.txt")~file_var

| 3. Network & Web Module |
Import($Website)@also%~web!`global`:web
<$web>("https://google.com")

4. Hệ thống Quản lý và Cài đặt Thư viện Ngoại vi (External Library & Package Management Engine)A. Lệnh Cài đặt qua Terminal (CLI Installer Directive)Để thêm một thư viện ngoại vi vào môi trường thực thi .ko, người dùng sử dụng lệnh Terminal:ko -install "Tên thư viện"

B. Nơi Đăng ký và Đóng gói Thư viện (Package Registry & Format)Đăng tải Thư viện: Mọi thư viện ngoại vi được đăng tải công khai tại cổng thông tin chính thức: ko-studio.ai.studio.Cơ chế GitHub Linking: Khi đăng tải thư viện lên ko-studio.ai.studio, nhà phát triển bắt buộc phải đăng kèm một đường dẫn kho chứa GitHub (GitHub Repository URL).Ngôn ngữ Phát triển Hỗ trợ: Thư viện ngoại vi có thể được viết bằng một hoặc nhiều ngôn ngữ lập trình sau:Java, Lua, Python, C, C++, Node.js, .ko, Zig.Định dạng Đóng gói Chuẩn: Toàn bộ bộ mã nguồn, tệp thực thi hoặc liên kết của thư viện bắt buộc phải được nén lại thành một tệp duy nhất định dạng .zip nằm trong kho lưu trữ GitHub.C. Quy trình Tự động Phân tích và Xử lý bởi Import.javaKhi lệnh ko -install "Tên thư viện" được gửi từ Terminal, Subsystem Import.java sẽ tự động kích hoạt tiến trình xử lý đa bước:$$\text{CLI Command} \xrightarrow{\text{ko -install}} \text{Query } \texttt{ko-studio.ai.studio} \xrightarrow{\text{Get GitHub URL}} \text{Clone Repo} \xrightarrow{\text{Zip Inspection \& Ingestion}} \text{Compile / Link}$$Clone Repo Tự động: Import.java truy vấn liên kết GitHub từ ko-studio.ai.studio và tự động thực hiện thao tác clone toàn bộ repository về thư mục tạm của hệ thống.Kiểm tra và Lọc tệp .zip (Repository Zip Verification):Trường hợp 1 (Tìm thấy tệp .zip): Import.java giữ lại duy nhất tệp .zip này và xóa sạch toàn bộ các tệp/thư mục còn lại có trong repository vừa clone.Trường hợp 2 (Không tìm thấy tệp .zip): Tiến trình dừng lại ngay lập tức và xóa sạch toàn bộ dữ liệu vừa clone.Giải nén và Biên dịch (Extraction & Compilation):Import.java tiếp nhận tệp .zip, tiến hành giải nén và phân tích ngôn ngữ phát triển (Java, Lua, Python, C, C++, Node.js, .ko, Zig) để kích hoạt trình biên dịch tương ứng.Xác minh Khả năng Hoạt động và Tự động Dọn dẹp (Failure Fallback & Auto-Deletion):Nếu quá trình biên dịch/kết nối thất bại hoặc thư viện gặp lỗi không thể hoạt động được, Import.java sẽ đưa ra thông báo lỗi chi tiết ra màn hình Terminal, đồng thời tự động xóa bỏ hoàn toàn thư viện đó khỏi hệ thống để tránh xung đột môi trường.VIII. LẬP TRÌNH HƯỚNG ĐỐI TƯỢNG (OBJECT-ORIENTED PROGRAMMING - OOP)1. Cấu trúc Lớp và Đóng gói (Encapsulation Rules)Công khai (Public): Mặc định mọi thuộc tính/phương thức nằm tự do trong Class đều là Public (ai bên ngoài cũng gọi được).Bảo mật (Private): Các thành phần nằm bên trong khối @private [ ] chỉ được phép truy cập từ bên trong chính Class đó.Monster !class [

    @private [
        string("Dragon")~name
        int(100)~hp

        take_damage() [
            int(<$random>(15, 35))~damage
            <now>(hp - damage)>hp
            <printf>^("Monster {name} bị đánh! HP còn: {hp}\n")
            <return>(hp)
        ]
    ]
]

2. Khởi tạo và Gọi Phương thứcTạo đối tượng (Instantiation): ~TênClass~tên_đối_tượngGọi phương thức: $tên_đối_tượng~tên_phương_thức()~Monster~m1                             | Tạo đối tượng m1 thuộc lớp Monster |
int($m1~take_damage())~remaining_hp     | Gọi hàm take_damage của m1 |

IX. CƠ CHẾ XỬ LÝ LỖI VÀ NGOẠI LỆ (ERROR & EXCEPTION HANDLING - <catch>)1. Cú pháp và Nguyên lý Thẻ <catch>Thẻ <catch> hoạt động như một "Lưới hứng lỗi". Khi chương trình gặp sự cố (chia cho 0, mất kết nối...), thay vì bị sập, luồng điều khiển sẽ rơi vào khối <catch>.$$\text{\texttt{<catch>}}(\text{\texttt{`ErrorCode`} \ \lor \ \text{Condition}}) \ [ \ \text{Khối\_Lệnh\_Xử\_Lý} \ ]$$2. Quy tắc Phạm vi Quét Lỗi (Scoped Upward Catching Rules)Quy tắc Bị Chặn Bởi Tầm Vực Khối Nội Cục (Scoped Block Boundary Rule)Khi thẻ <catch> được đặt bên trong một Hàm [ ] hoặc Khối Main [ ], hành vi quét ngược của nó bị giới hạn nghiêm ngặt trong phạm vi của chính Hàm/Khối Main đó.Thẻ <catch> nội cục chỉ bảo vệ các câu lệnh nằm phía trên nó và cùng nằm trong khối đó (tính từ vị trí thẻ <catch> ngược lên đến đầu khối [).Nó tuyệt đối không quét lan ra bên ngoài hoặc bảo vệ các hàm/khối khác ngoài tầm vực nội cục của nó.process_data(int~a, int~b) [
    int(a / b)~result
    <printf>^("Kết quả: {result}\n")

    | Thẻ catch này NẰM TRONG hàm process_data |
    | Chỉ quét ngược đến đầu hàm process_data và BẮT LỖI NỘI CỤC hàm này |
    <catch>(`DivideByZeroError`) [
        <printf>^("Lỗi chia cho 0 bên trong hàm process_data!\n")
        <return>(0)
    ]
]

Quy tắc Quét Ngược Toàn Cục / Đa Khối (Global Upward Multi-Block Catching Rule)Khi thẻ <catch> nằm ở phạm vi Toàn cục (Global Scope) (bên ngoài tất cả các hàm và khối Main):Thẻ sẽ quét ngược lên phía trên và bảo vệ cho tất cả các Hàm, Khối Main hoặc câu lệnh toàn cục nằm trước nó.fun_a() [ ... ]
fun_b() [ ... ]

| Thẻ catch đặt ở toàn cục: BẢO VỆ CẢ fun_a() LẪN fun_b() |
<catch>(`SystemException`) [
    <printf>^("Bắt lỗi toàn cục phát sinh từ fun_a hoặc fun_b!\n")
]

Quy tắc Ưu tiên Chuỗi Catch Top-Down (Sequential Cascade Rule)Khi xếp nhiều thẻ <catch> nối tiếp nhau, hệ thống sẽ kiểm tra từ trên xuống dưới. Thẻ nào khớp lỗi trước sẽ xử lý và dừng lại (First-Matched, First-Served).3. Cấu trúc Biến Ngoại lệ Nội tại (error Dictionary)Khi khối <catch> được kích hoạt, hệ thống tự động tạo ra một từ điển chứa chi tiết về lỗi:error<"line">: Số dòng bị lỗi trong mã nguồn.error<"code">: Đoạn mã .ko trực tiếp gây ra lỗi.error<"type">: Tên định danh của loại lỗi (DivideByZeroError, SystemException, ...).<catch>(`DivideByZeroError`) [
    <printf>^("Lỗi {error<"type">} tại dòng {error<"line">}: đoạn mã '{error<"code">' bị sự cố!\n")
]

---

## X. CHƯƠNG TRÌNH MẪU HOÀN CHỈNH (COMPLETE SYSTEM DEMO PROGRAM)
```ko
| ========================================================== |
| 1. Nạp Thư viện Chuẩn (Xử lý bởi Import.java Subsystem)    |
| ========================================================== |
Import($Random)@also%~random!`global`:random
Import($Os)@also%~os!`global`:os
Import($Website)@also%~web!`global`:web

| ========================================================== |
| 2. Định nghĩa các Hàm Hệ thống                             |
| ========================================================== |
init_system_logs() [
    <printf>^("=== KHOI TAO HE THONG .KO ===\n")
    <$os>("log.txt")~log_file
    <$web>domain("mygame.com")@app_server
    <$web>("https://api.mygame.com/status")
    <return>(\True\)
]

safe_divide(int~dividend, int~divisor) [
    int(dividend / divisor)~result
    int(dividend % divisor)~remainder
    <printf>^("Thương: {result}, Dư: {remainder}\n")
    <return>(result)

    | Catch Nội Cục: Chỉ quét và bắt lỗi bên trong hàm safe_divide |
    <catch>(`DivideByZeroError`) [
        <printf>^("Lỗi {error<"type">} tại dòng {error<"line">}: {error<"code">}. Trả về 0.\n")
        <return>(0)
    ]
]

calculate_crit_damage(int~base_dmg, int~bonus_dmg) [
    int((base_dmg + bonus_dmg) * 2)~crit_dmg
    <return>(crit_dmg)
]

| ---------------------------------------------------------- |
| Catch Toàn cục: Quét ngược bảo vệ các hàm ở cấp toàn cục  |
| ---------------------------------------------------------- |
<catch>(`SystemException`) [
    <printf>^("Bắt lỗi hệ thống tổng quát phát sinh từ cấp toàn cục!\n")
    <return>(-1)
]

| ========================================================== |
| 3. Định nghĩa Lớp Hero (OOP System)                        |
| ========================================================== |
Hero !class [
    @private [
        string("")~name
        int(100)~hp
        ('Kiem', 'Khien', 'Binh mau')~inventory

        setup_player() [
            <input>("Nhap ten anh hung cua ban: \n")&=name
            <printf>^("Chao mung anh hung {name} den voi the gioi .ko!\n")
            <return>(name)
        ]

        use_random_item() [
            int(<len>^(inventory))~inv_len
            int(<$random>(0, inv_len - 1))~item_index
            <printf>^("Hero {name} used item: {inventory<{item_index}>}\n")
            <return>(inventory<{item_index}>)
        ]

        check_status() [
            <if>(hp >= 80 && hp <= 100) [
                <printf>^("Trang thai: Rat khoe\n")
            ]
            <elif>(hp >= 30 %% hp < 80) [
                <printf>^("Trang thai: Binh thuong\n")
            ]
            <else> [
                <printf>^("Trang thai: Nguy hiem!\n")
            ]
            <return>(hp)
        ]
    ]
]

| ========================================================== |
| 4. Khối Thực thi Chính (Main Entry Point Block)           |
| ========================================================== |
[
    booling(~init_system_logs())~is_ready
    
    ~Hero~p1
    string($p1~setup_player())~player_name
    
    | Thử nghiệm biểu diễn Nhị phân (byte) và Vùng đệm Hex (bytes) |
    byte("A")~binary_char
    bytes(8)~hex_buffer
    <printf>^("Mã nhị phân chữ A: {binary_char}\n")
    
    | Thử nghiệm thẻ hệ thống đo độ dài <len> |
    int(<len>^("Xin chào .ko\n"))~str_len
    int(<len>^(hex_buffer))~buf_len
    <printf>^("Độ dài chuỗi: {str_len}, Kích thước bộ đệm: {buf_len}\n")

    | Thử nghiệm thẻ hệ thống mã hóa <encode> |
    <encode(`UTF-8`)>^("Mã hóa UTF-8 trực tiếp\n")
    bytes(<encode(`ASCII`)>^("Hello .ko"))~asc_bytes
    int(<len>^(asc_bytes))~encoded_len
    <printf>^("Độ dài mảng byte mã hóa ASCII: {encoded_len}\n")
    
    | Thử nghiệm hàm safe_divide với phép chia cho 0 |
    int(~safe_divide(100, 0))~calc_test
    <printf>^("Kết quả kiểm tra chia an toàn: {calc_test}\n")

    | Vòng lặp đếm i từ 1 đến 5 (Xử lý bởi Loop.cpp Subsystem) |
    Loop <for>(~i=1(2)&=5) [
        <printf>^("--- Turn {i} ---\n")
        string($p1~use_random_item())~used_item
    ]
    
    int($p1~check_status())~current_hp
    int(~calculate_crit_damage(50, 10))~final_strike
    <printf>^("Sát thương chí mạng tính toán được: {final_strike}\n")

    | Thao tác bộ nhớ trực tiếp và giải phóng vùng nhớ |
    int(999)~temp_data
    <printf>^("Địa chỉ ô nhớ temp_data: {<memory>^temp_data}\n")
    <memory>dete(temp_data)

    | Catch nội cục trong Main: Bắt lỗi xảy ra trong khối Main |
    <catch>(`GlobalError`) [
        <printf>^("Bắt lỗi ngoại lệ trong Main tại dòng {error<"line">}: {error<"code">\n}")
    ]
]

