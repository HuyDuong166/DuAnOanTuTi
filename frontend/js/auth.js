if (typeof window.API_BASE === 'undefined') {
    window.API_BASE = window.location.origin;
}

// Khai báo hàm chuyển đổi Form trực tiếp vào window
window.toggleForm = function() {
    const loginBox = document.getElementById('loginBox');
    const registerBox = document.getElementById('registerBox');
    if (!loginBox || !registerBox) return;

    if (loginBox.style.display === 'none') {
        loginBox.style.display = 'block';
        registerBox.style.display = 'none';
    } else {
        loginBox.style.display = 'none';
        registerBox.style.display = 'block';
    }
};

window.showRegisterForm = function() {
    const loginBox = document.getElementById('loginBox');
    const registerBox = document.getElementById('registerBox');
    if (loginBox) loginBox.style.display = 'none';
    if (registerBox) registerBox.style.display = 'block';
};

window.showLoginForm = function() {
    const loginBox = document.getElementById('loginBox');
    const registerBox = document.getElementById('registerBox');
    if (loginBox) loginBox.style.display = 'block';
    if (registerBox) registerBox.style.display = 'none';
};

// Đăng ký sự kiện khi trang đã tải xong DOM
document.addEventListener('DOMContentLoaded', () => {
    // Xử lý Form Đăng Ký
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('r_email').value;
            const username = document.getElementById('r_user').value;
            const password = document.getElementById('r_pass').value;
            const admin_code = document.getElementById('r_admin_code')?.value || null;

            try {
                const res = await fetch(`${window.API_BASE}/api/auth/register`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ email, username, password, admin_code })
                });
                const data = await res.json();
                
                if (res.ok) {
                    if (data.is_admin) {
                        alert("🎉 Đăng ký thành công tài khoản BAN TỔ CHỨC (Admin)!");
                    } else {
                        alert("✅ Đăng ký thành công tài khoản NGƯỜI CHƠI (Sinh viên)!");
                    }
                    window.showLoginForm();
                } else {
                    alert("Lỗi: " + (data.detail || "Đăng ký thất bại"));
                }
            } catch (err) {
                alert("Không thể kết nối đến Máy chủ (Backend đang tắt?)");
            }
        });
    }

    // Xử lý Form Đăng Nhập
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('l_user').value;
            const password = document.getElementById('l_pass').value;

            try {
                const params = new URLSearchParams();
                params.append('username', username);
                params.append('password', password);

                const res = await fetch(`${window.API_BASE}/api/auth/login`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: params
                });
                
                const data = await res.json();
                
                if (res.ok) {
                    alert("Đăng nhập thành công!");
                    sessionStorage.setItem('access_token', data.access_token);
                    window.location.href = 'index.html';
                } else {
                    alert("Lỗi: " + (data.detail || "Sai tên đăng nhập hoặc mật khẩu"));
                }
            } catch (err) {
                alert("Không thể kết nối đến Máy chủ (Backend đang tắt?)");
            }
        });
    }
});