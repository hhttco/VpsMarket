sudo apt update && sudo apt install python3 python3-pip python3-venv nginx git -y && systemctl enable --now nginx && cd /var/www

sudo mkdir -p /var/www/vps_market && cd /var/www/vps_market && python3 -m venv venv && source venv/bin/activate && pip install Flask Flask-SQLAlchemy Flask-Login

/var/www/vps_market/venv/bin/pip install gunicorn Pillow

sqlite3 /var/www/vps_market/vps.db "SELECT * FROM user;"

vim /etc/systemd/system/vpsmarket.service
[Unit]
Description=Flask VPS Market Application
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/vps_market
ExecStart=/var/www/vps_market/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target


sudo systemctl daemon-reload
sudo systemctl start vpsmarket
sudo systemctl enable vpsmarket
sudo systemctl restart vpsmarket


vim /etc/nginx/conf.d/vps_market.conf

# =========================================================================
# 🚀 工业级 VPS 交易中枢 - 高防护纯 HTTP Nginx 配置文件
# =========================================================================

# 1. 基础防护模块：建立全局限频与并发连接池（防止高频暴力刷新和 DoS 挤爆）
limit_req_zone $binary_remote_addr zone=req_limit_per_ip:10m rate=15r/s;
limit_conn_zone $binary_remote_addr zone=conn_limit_per_ip:10m;

server {
    server_name vps.12332167.xyz;

    # 隐藏 Nginx 版本号，防止黑客通过特定版本已知漏洞进行针对性攻击
    server_tokens off;

    # ---------------------------------------------------------------------
    # 🛡️ 顶级生产环境大厂级安全响应头（纵深防御，封杀 XSS 与凭证劫持）
    # ---------------------------------------------------------------------
    # 防御点击劫持：禁止恶意镜像网站通过 iframe 框架嵌套你的交易集市
    add_header X-Frame-Options "SAMEORIGIN" always;
    # 防御跨站脚本攻击 (XSS)：强制开启浏览器底层的恶意脚本拦截过滤机制
    add_header X-XSS-Protection "1; mode=block" always;
    # 拒绝MIME类型嗅探：强制浏览器严格遵守你返回的数据类型声明，封杀隐蔽式木马
    add_header X-Content-Type-Options "nosniff" always;
    # 隐私保护头：在跳转外部商家官网时，仅传递基本域名，隐藏本站的精确交易路由URL
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # ---------------------------------------------------------------------
    # 🕷️ 恶意网络爬虫、扫描探测工具黑名单（一网打尽网络垃圾）
    # ---------------------------------------------------------------------
    if ($http_user_agent ~* (Scrapy|Curl|HttpClient|python-requests|Grabber|Wget|python|Java|Go-http-client|Go|perl|ruby|WebBench|dirbuster|sqlmap|nmap|scan|Gecko/20100101)) {
        return 403; # 直接拒绝连接，保护卖家联系方式不被脚本瞬间拉走
    }

    # ---------------------------------------------------------------------
    # 📦 静态资源全权托管（由 Nginx 原生飞速秒开，不再惊动后端 Python）
    # ---------------------------------------------------------------------
    location /static/ {
        alias /var/www/vps_market/static/;
        expires 30d; # 缓存 30 天，减轻服务器带宽开销
        access_log off;
        log_not_found off;
    }

    # ---------------------------------------------------------------------
    # 🗄️ 数据库与核心代码物理防窥视（封杀黑客探针扫描）
    # ---------------------------------------------------------------------
    location ~* \.(db|sqlite|sqlite3|py|sh|ini|log|git|env)$ {
        deny all; # 任何人直接读取 .db 数据库或 .py 源码，直接返回 403 封锁
        return 404;
    }

    # ---------------------------------------------------------------------
    # ⚙️ 核心反向代理中枢（数据交由 Gunicorn / Flask 守护进程）
    # ---------------------------------------------------------------------
    location / {
        # 激活并发限制：单个 IP 在这里同时最多只能建立 10 个连接，防 CC 攻击
        limit_conn conn_limit_per_ip 10;
        # 激活频次限制：每秒允许 15 次请求，瞬间爆发允许缓冲 10 个包，不延时响应
        limit_req zone=req_limit_per_ip burst=10 nodelay;

        # 核心数据代理投递
        proxy_pass http://127.0.0.1:5000;
        
        # 严格透传真实的客户端用户 IP 数据，防止 Flask 读取到全是 127.0.0.1
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 高级连接超时平滑控制（防止黑客通过恶意挂起连接耗尽系统句柄）
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # ---------------------------------------------------------------------
    # 🎨 高级高防自定义报错视窗（隐藏 Nginx 原生简陋页面，不暴露中间件底盘）
    # ---------------------------------------------------------------------
    error_page 403 404 /static/404.html;
    error_page 500 502 503 504 /static/500.html;
}


sudo systemctl restart nginx
