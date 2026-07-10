import os
import random
import io
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from PIL import Image, ImageDraw
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'vps.db')}"
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)

class VPS(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(50), nullable=False)
    cpu = db.Column(db.String(20), nullable=False)
    memory = db.Column(db.String(20), nullable=False)
    disk = db.Column(db.String(20), nullable=False)
    bandwidth = db.Column(db.String(20), nullable=False)
    port_speed = db.Column(db.String(20), nullable=False)
    
    # 转换为纯数字字段方便高精计算（单位：元）
    sale_price = db.Column(db.Float, nullable=False)      
    renewal_price = db.Column(db.Float, nullable=False)   
    renewal_cycle = db.Column(db.Integer, default=365)     # 续费周期天数（如月付30，年付365）
    expiry_date = db.Column(db.String(20), nullable=False)  # 🚀 新增：合同到期日 (YYYY-MM-DD)
    
    contact = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 核心计算中枢：处理折价率与倒计时数据
def process_vps_analytics(vps_list):
    today = datetime.now().date()
    for vps in vps_list:
        try:
            exp_date = datetime.strptime(vps.expiry_date, '%Y-%m-%d').date()
            remaining_days = (exp_date - today).days
            vps.remaining_days = max(0, remaining_days)
            
            # 计算剩余价值：(续费原价 / 周期) * 剩余天数
            daily_cost = vps.renewal_price / vps.renewal_cycle
            vps.residual_value = round(daily_cost * vps.remaining_days, 2)
            
            # 计算折价率 / 折损幅度
            if vps.residual_value > 0:
                discount = (1 - (vps.sale_price / vps.residual_value)) * 100
                vps.discount_rate = round(discount, 1)
            else:
                vps.discount_rate = -100
        except Exception:
            vps.remaining_days = 0
            vps.residual_value = 0
            vps.discount_rate = 0
    return vps_list

@app.route('/')
def index():
    raw_list = VPS.query.filter_by(is_active=True).all()
    vps_list = process_vps_analytics(raw_list)
    return render_template('index.html', vps_list=vps_list)

@app.route('/my-listings')
@login_required
def my_listings():
    raw_list = VPS.query.filter_by(user_id=current_user.id).all()
    vps_list = process_vps_analytics(raw_list)
    return render_template('my_listings.html', vps_list=vps_list)

@app.route('/toggle-listing/<int:vps_id>')
@login_required
def toggle_listing(vps_id):
    vps = VPS.query.get_or_404(vps_id)
    if vps.user_id != current_user.id:
        flash('越权操作拦截')
        return redirect(url_for('index'))
    vps.is_active = not vps.is_active
    db.session.commit()
    flash('货架状态更新成功')
    return redirect(url_for('my_listings'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('用户名或密码错误')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_captcha = request.form.get('captcha', '').strip().lower()
        real_captcha = session.get('captcha_text', '').lower()

        if not user_captcha or user_captcha != real_captcha:
            flash('验证码输入错误，请重试')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('用户名已存在')
        else:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            session.pop('captcha_text', None)
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/captcha')
def get_captcha():
    chars = '23456789abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ'
    captcha_text = ''.join(random.choice(chars) for _ in range(4))
    session['captcha_text'] = captcha_text

    width, height = 120, 45
    img = Image.new('RGB', (width, height), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)

    for _ in range(4):
        draw.line([(random.randint(0, width), random.randint(0, height)), 
                   (random.randint(0, width), random.randint(0, height))], 
                  fill=(59, 130, 246), width=1)

    for i, char in enumerate(captcha_text):
        draw.text((15 + i * 24, random.randint(5, 15)), char, fill=(16, 185, 129))

    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route('/publish', methods=['GET', 'POST'])
@login_required
def publish():
    if request.method == 'POST':
        new_vps = VPS(
            provider=request.form.get('provider'),
            location=request.form.get('location'),
            cpu=request.form.get('cpu'),
            memory=request.form.get('memory'),
            disk=request.form.get('disk'),
            bandwidth=request.form.get('bandwidth'),
            port_speed=request.form.get('port_speed'),
            sale_price=float(request.form.get('sale_price', 0)),
            renewal_price=float(request.form.get('renewal_price', 0)),
            renewal_cycle=int(request.form.get('renewal_cycle', 365)),
            expiry_date=request.form.get('expiry_date'), # 捕获到期日
            contact=request.form.get('contact'),
            user_id=current_user.id
        )
        db.session.add(new_vps)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('publish.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
