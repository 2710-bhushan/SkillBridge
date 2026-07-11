import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'p2p-skill-exchange-secret-888'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///skill_exchange.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='student') # student, admin

class SkillListing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skill_name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(10), nullable=False) # 'offer' (teaches) or 'want' (wants to learn)
    proficiency = db.Column(db.String(20), nullable=False) # Beginner, Intermediate, Expert
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('User', backref=db.backref('skills', lazy=True))

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    skill_name = db.Column(db.String(100), nullable=False)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    learner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='Pending') # Pending, Approved, Completed, Cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    mentor = db.relationship('User', foreign_keys=[mentor_id], backref='mentor_sessions')
    learner = db.relationship('User', foreign_keys=[learner_id], backref='learner_sessions')

class SessionReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False) # 1 to 5
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    booking = db.relationship('Booking', backref=db.backref('reviews', lazy=True))
    reviewer = db.relationship('User')

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Seed Data
def seed_data():
    if User.query.first() is None:
        admin = User(email='admin@campus.edu', name='P2P Exchange Admin', role='admin', password_hash=generate_password_hash('admin123'))
        s1 = User(email='student1@campus.edu', name='Bruce Wayne', password_hash=generate_password_hash('student123'))
        s2 = User(email='student2@campus.edu', name='Clark Kent', password_hash=generate_password_hash('student123'))
        s3 = User(email='student3@campus.edu', name='Diana Prince', password_hash=generate_password_hash('student123'))
        
        db.session.add_all([admin, s1, s2, s3])
        db.session.commit()

        # Seed listings
        l1 = SkillListing(student_id=s1.id, skill_name='Python Programming', type='offer', proficiency='Expert', description='Can teach Flask, pandas, and data structures. Looking to exchange for copywriting or writing skills.')
        l2 = SkillListing(student_id=s1.id, skill_name='Spanish', type='want', proficiency='Beginner', description='Looking for native speakers or advanced students to practice conversational Spanish.')
        
        l3 = SkillListing(student_id=s2.id, skill_name='Spanish', type='offer', proficiency='Expert', description='Native speaker. Happy to teach conversational Spanish. Want to learn coding.')
        l4 = SkillListing(student_id=s2.id, skill_name='Python Programming', type='want', proficiency='Beginner', description='Need help understanding web design and database scripting.')

        l5 = SkillListing(student_id=s3.id, skill_name='Copywriting', type='offer', proficiency='Intermediate', description='Can help write clean resumes, essays, or marketing scripts.')

        db.session.add_all([l1, l2, l3, l4, l5])
        db.session.commit()

# Mutual Matching Engine
# Finds partners who offer what the current user wants, AND want what the current user offers
def find_mutual_matches(user_id):
    user_wants = [l.skill_name.lower() for l in SkillListing.query.filter_by(student_id=user_id, type='want').all()]
    user_offers = [l.skill_name.lower() for l in SkillListing.query.filter_by(student_id=user_id, type='offer').all()]
    
    if not user_wants or not user_offers:
        return []

    # Find candidates
    candidates = SkillListing.query.filter(SkillListing.student_id != user_id).all()
    partners = {}
    
    for item in candidates:
        partner_id = item.student_id
        if partner_id not in partners:
            partners[partner_id] = {'offers': [], 'wants': [], 'user': item.student}
        
        if item.type == 'offer':
            partners[partner_id]['offers'].append(item.skill_name.lower())
        else:
            partners[partner_id]['wants'].append(item.skill_name.lower())

    matches = []
    for pid, data in partners.items():
        # Intersection: Partner offers what user wants, and partner wants what user offers
        partner_gives_what_user_wants = set(data['offers']).intersection(user_wants)
        partner_wants_what_user_gives = set(data['wants']).intersection(user_offers)
        
        if partner_gives_what_user_wants and partner_wants_what_user_gives:
            matches.append({
                'partner': data['user'],
                'you_get': list(partner_gives_what_user_wants),
                'they_get': list(partner_wants_what_user_gives)
            })

    return matches

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    search = request.args.get('search', '')
    filter_type = request.args.get('type', '')
    
    # Base query for other students' skill cards
    query = SkillListing.query.filter(SkillListing.student_id != current_user.id)
    if search:
        query = query.filter((SkillListing.skill_name.contains(search)) | (SkillListing.description.contains(search)))
    if filter_type:
        query = query.filter(SkillListing.type == filter_type)
        
    listings = query.order_by(SkillListing.created_at.desc()).all()
    
    # Mutual matches list
    matches = find_mutual_matches(current_user.id)
    
    # User's bookings
    bookings = Booking.query.filter(
        (Booking.mentor_id == current_user.id) | (Booking.learner_id == current_user.id)
    ).order_by(Booking.scheduled_at.desc()).all()

    # User's own listings
    my_listings = SkillListing.query.filter_by(student_id=current_user.id).all()

    return render_template('dashboard.html', listings=listings, matches=matches, bookings=bookings, my_listings=my_listings)

@app.route('/add-listing', methods=['POST'])
@login_required
def add_listing():
    skill_name = request.form.get('skill_name')
    type_ = request.form.get('type')
    proficiency = request.form.get('proficiency')
    description = request.form.get('description')

    if not skill_name or not type_ or not proficiency or not description:
        flash('Please fill in all fields.', 'error')
        return redirect(url_for('dashboard'))

    new_listing = SkillListing(
        student_id=current_user.id,
        skill_name=skill_name,
        type=type_,
        proficiency=proficiency,
        description=description
    )
    db.session.add(new_listing)
    db.session.commit()
    flash('Skill exchange listing published!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/book-session', methods=['POST'])
@login_required
def book_session():
    skill_name = request.form.get('skill_name')
    mentor_id = request.form.get('mentor_id', type=int)
    date_str = request.form.get('scheduled_at')

    if not skill_name or not mentor_id or not date_str:
        flash('Missing details to book session.', 'error')
        return redirect(url_for('dashboard'))

    scheduled_at = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')

    booking = Booking(
        skill_name=skill_name,
        mentor_id=mentor_id,
        learner_id=current_user.id,
        scheduled_at=scheduled_at,
        status='Pending'
    )
    db.session.add(booking)
    db.session.commit()
    flash('Session booked! Waiting for mentor confirmation.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/update-booking/<int:booking_id>', methods=['POST'])
@login_required
def update_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    action = request.form.get('action') # 'Approve', 'Completed', 'Cancelled'

    if booking.mentor_id != current_user.id and booking.learner_id != current_user.id:
        flash('Unauthorized action.', 'error')
        return redirect(url_for('dashboard'))

    if action in ['Approved', 'Completed', 'Cancelled']:
        booking.status = action
        db.session.commit()
        flash(f'Session marked as {action.lower()}!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/submit-review/<int:booking_id>', methods=['POST'])
@login_required
def submit_review(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    rating = request.form.get('rating', type=int)
    comment = request.form.get('comment', '')

    if rating < 1 or rating > 5:
        flash('Invalid rating score.', 'error')
        return redirect(url_for('dashboard'))

    review = SessionReview(
        booking_id=booking.id,
        reviewer_id=current_user.id,
        rating=rating,
        comment=comment
    )
    db.session.add(review)
    db.session.commit()
    flash('Thank you for rating your session!', 'success')
    return redirect(url_for('dashboard'))

# Chat APIs
@app.route('/api/chat/messages/<int:partner_id>')
@login_required
def get_chat_messages(partner_id):
    messages = ChatMessage.query.filter(
        ((ChatMessage.sender_id == current_user.id) & (ChatMessage.receiver_id == partner_id)) |
        ((ChatMessage.sender_id == partner_id) & (ChatMessage.receiver_id == current_user.id))
    ).order_by(ChatMessage.created_at.asc()).all()
    
    # Mark incoming messages as read
    ChatMessage.query.filter_by(sender_id=partner_id, receiver_id=current_user.id, is_read=False).update({ChatMessage.is_read: True})
    db.session.commit()

    return jsonify([{
        'id': m.id,
        'sender_id': m.sender_id,
        'sender_name': m.sender.name,
        'content': m.content,
        'created_at': m.created_at.strftime('%Y-%m-%d %H:%M')
    } for m in messages])

@app.route('/api/chat/send', methods=['POST'])
@login_required
def send_chat_message():
    receiver_id = request.form.get('receiver_id', type=int)
    content = request.form.get('content')

    if not receiver_id or not content:
        return jsonify({'error': 'Missing recipient or content.'}), 400

    msg = ChatMessage(sender_id=current_user.id, receiver_id=receiver_id, content=content)
    db.session.add(msg)
    db.session.commit()

    return jsonify({
        'id': msg.id,
        'sender_id': msg.sender_id,
        'sender_name': msg.sender.name,
        'content': msg.content,
        'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M')
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(debug=True, port=5004)
