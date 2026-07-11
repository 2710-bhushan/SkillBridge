# Peer-to-Peer Skill Exchange

A barter-style student learning platform that allows peers to exchange skills without transaction fees. Students list what they can teach (offers) and what they want to learn (wants), and the matching engine automatically connects compatible exchange pairs.

## Features

- **Mutual Match Recommendation Engine:** Highlights users who offer what you want to learn, AND want what you teach, for direct reciprocal trades.
- **In-App Live Chat:** Conversation window with AJAX polling for instant, real-time messaging.
- **Session Scheduling Calendar:** Book mentoring lessons or accept classes on calendar slots.
- **Feedback & Rating Reviews:** Five-star rating selector and feedback remarks for completed courses.
- **Categorized Search Board:** Easily search and filter listings.

## Tech Stack

- **Backend:** Python 3, Flask, SQLite, SQLAlchemy.
- **Frontend:** HTML5, CSS3, JavaScript (polling, dynamic messaging, star-hover gauges), Boxicons.

## Setup & Running

1. Open a terminal in this directory (`5-p2p-skill-exchange`).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the server:
   ```bash
   python app.py
   ```
4. Access the site at `http://127.0.0.1:5004`.

> **Demo Credentials:** See `demo_credentials.txt` in this folder.
