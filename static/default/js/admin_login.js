const adminLoginForm = document.getElementById('admin-login-form');
if (adminLoginForm) {
    adminLoginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const errorMessage = document.getElementById('error-message');
        
        try {
            const response = await fetch('/api/admin/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });
            
            if (response.ok) {
                // 登录成功，重定向到管理员首页
                window.location.href = '/admin';
            } else {
                const errorData = await response.json();
                errorMessage.textContent = errorData.detail || '登录失败';
                errorMessage.style.display = 'block';
            }
        } catch (error) {
            errorMessage.textContent = '网络错误，请稍后重试';
            errorMessage.style.display = 'block';
        }
    });
}