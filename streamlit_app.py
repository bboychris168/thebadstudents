import streamlit as st
import json
import os

DB_PATH = "badminton_db.json"

def load_db():
    if not os.path.exists(DB_PATH):
        return {"players": [], "games": []}
    with open(DB_PATH, "r") as f:
        return json.load(f)

def save_db(db):
    # Only save games
    with open(DB_PATH, "w") as f:
        json.dump({"games": db.get("games", [])}, f, indent=2)

def get_next_game(players, games, players_per_game=4):
    # Initialize tracking dictionaries
    consecutive_plays = {p: 0 for p in players}  # Track consecutive games played
    consecutive_sits = {p: 0 for p in players}   # Track consecutive games sat out
    play_counts = {p: 0 for p in players}        # Track total games played
    last_played_with = {p: set() for p in players}  # Track who each player last played with
    
    # Update tracking based on game history
    for i, game in enumerate(games):
        # Update play counts and consecutive tracking
        for p in players:
            if p in game:
                play_counts[p] += 1
                consecutive_plays[p] = consecutive_plays.get(p, 0) + 1
                consecutive_sits[p] = 0
                # Update who this player played with in their last game
                if i == len(games) - 1:  # If this was the last game
                    last_played_with[p] = set(g for g in game if g != p)
            else:
                consecutive_plays[p] = 0
                consecutive_sits[p] = consecutive_sits.get(p, 0) + 1
    
    # If we have 4 or fewer players, they all play
    if len(players) <= players_per_game:
        return {"playing": players, "sitting": [], "play_counts": play_counts}
    
    # Calculate priority scores for each player
    player_scores = {}
    for p in players:
        score = 0
        # Must play if sat out twice in a row
        if consecutive_sits[p] >= 2:
            score -= 10000  # Very high priority to play
        # Heavily penalize any consecutive sits
        elif consecutive_sits[p] > 0:
            score -= 1000 * consecutive_sits[p]
        # Penalize consecutive plays beyond 2
        if consecutive_plays[p] >= 2:
            score += 1000 * consecutive_plays[p]
        # Consider total play count for fine-tuning
        score += play_counts[p] * 10
        player_scores[p] = score

    # Sort players by their priority score (lower score = higher priority to play)
    sorted_players = sorted(players, key=lambda p: (player_scores[p], play_counts[p], p))
    
    # Function to check if a player combination is valid
    def is_valid_combination(current_players):
        # Check each player against others in the group
        for p1 in current_players:
            # Count how many players from their last game are in this game
            overlap = len(last_played_with[p1].intersection(set(current_players)))
            if overlap >= 2:  # Allow at most one player from previous game
                return False
        return True
    
    # Function to find the best valid player to add
    def find_best_player(current_players, candidates):
        for p in candidates:
            if p not in current_players:
                test_group = current_players + [p]
                if is_valid_combination(test_group):
                    return p
        return None
    
    # Make adjustments to ensure no more than 2 consecutive sits and avoid same groups
    playing = []
    
    # First, add players who must play (sat out twice already)
    for p in sorted_players:
        if len(playing) >= players_per_game:
            break
        if consecutive_sits[p] >= 2:
            if not playing or is_valid_combination(playing + [p]):
                playing.append(p)
    
    # Then add players who haven't played recently
    for p in sorted_players:
        if len(playing) >= players_per_game:
            break
        if p not in playing and (consecutive_sits[p] > 0 or consecutive_plays[p] < 2):
            if is_valid_combination(playing + [p]):
                playing.append(p)
    
    # If we still need more players, add from the remaining ones
    remaining = [p for p in sorted_players if p not in playing]
    while len(playing) < players_per_game:
        next_player = find_best_player(playing, remaining)
        if next_player:
            playing.append(next_player)
            remaining.remove(next_player)
        else:
            # If no valid player found, just add the next available one
            next_player = next((p for p in remaining if p not in playing), None)
            if next_player:
                playing.append(next_player)
                remaining.remove(next_player)
            else:
                break
    
    # The rest sit out
    sitting = [p for p in players if p not in playing]
    
    return {"playing": playing, "sitting": sitting, "play_counts": play_counts}

st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center;'>🏸 Badminton Game Scheduler</h1>", unsafe_allow_html=True)
db = load_db()
games = db.get("games", [])






# Single column: Add Players, then Next Game below
st.subheader("Add Players")
player_input = st.text_area(
    "Enter player names, one per line:",
    placeholder="e.g. Alice\nBob\nCharlie\nDiana",
    height=250
)
players = [p.strip() for p in player_input.splitlines() if p.strip()]
if len(players) < 2:
    st.info("Please enter at least two player names to start.")
    st.stop()
st.write(", ".join(players))

# Get next game players and those sitting out
game_info = get_next_game(players, games, players_per_game=4)
next_game = game_info["playing"]
sitting_players = game_info["sitting"]
play_counts = game_info["play_counts"]

st.subheader("Next Game")
# Display players who will play
st.markdown(
    f"""
    <div style="
        background: linear-gradient(90deg, #ffecd2 0%, #fcb69f 100%);
        border-radius: 16px;
        padding: 1.5em 1em;
        margin-bottom: 1.2em;
        box-shadow: 0 2px 12px rgba(252, 182, 159, 0.18);
        text-align: center;
        font-size: 1.6em;
        font-weight: bold;
        color: #d7263d;
        letter-spacing: 0.04em;">
        {'<br>'.join(next_game)}
    </div>
    """,
    unsafe_allow_html=True
)

# Display players sitting out if any
if sitting_players:
    st.markdown(
        f"""
        <div style="
            background: #f8f9fa;
            border-radius: 8px;
            padding: 1em;
            margin-bottom: 1em;
            text-align: center;
            color: #6c757d;">
            <p style="margin: 0;">Sitting out this game:</p>
            <p style="margin: 0; font-weight: bold;">{', '.join(sitting_players)}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# Large, green native Streamlit button
st.markdown(
    """
    <style>
    div.stButton > button#play-next-game-btn {
        width: 100%;
        padding: 1.2em 0;
        font-size: 1.5em;
        font-weight: bold;
        color: #fff;
        background: linear-gradient(90deg, #43e97b 0%, #38f9d7 100%);
        border: none;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(67, 233, 123, 0.18);
        cursor: pointer;
        margin-top: 1.5em;
        margin-bottom: 1em;
        transition: background 0.2s, transform 0.1s;
    }
    div.stButton > button#play-next-game-btn:hover {
        background: linear-gradient(90deg, #38f9d7 0%, #43e97b 100%);
        transform: scale(1.03);
    }
    /* Style for reset button */
    div.stButton > button[data-baseweb="button"]:first-child {
        background-color: #ff6b6b;
        color: white;
        border: none;
        transition: background-color 0.3s;
    }
    div.stButton > button[data-baseweb="button"]:first-child:hover {
        background-color: #ff5252;
    }
    </style>
    <script>
    // Add id to the next Streamlit button
    const btns = window.parent.document.querySelectorAll('button');
    for (const btn of btns) {
        if (btn.innerText === 'Play Next Game') {
            btn.id = 'play-next-game-btn';
        }
    }
    </script>
    """,
    unsafe_allow_html=True
)
if st.button("Play Next Game", key="play_next_game_btn", help="Add this game to the schedule"):
    db["games"].append(next_game)  # next_game is already just the playing players
    save_db(db)
    success_msg = f"Game added with players: {', '.join(next_game)}"
    if sitting_players:
        success_msg += f"\nSitting out: {', '.join(sitting_players)}"
    st.success(success_msg)
    st.rerun()

# Previous games section below
st.subheader("Previous Games")

# Add reset button in a container with confirmation
reset_col1, reset_col2 = st.columns([1, 4])
with reset_col1:
    if st.button("Reset Games", type="primary", help="Clear all game history and start fresh"):
        # Add confirmation dialog
        confirm = st.button("Click again to confirm reset", key="confirm_reset", type="secondary")
        if confirm:
            # Reset the database by creating a new empty one
            db = {"games": []}
            save_db(db)
            st.success("Game history has been reset!")
            st.rerun()

# Show games if they exist
if games:
    # Create a consistent color mapping for each unique player
    all_players = set()
    for game in games:
        all_players.update(game)
    
    # Generate a unique color for each player using a predefined color palette
    colors = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", 
        "#FFEEAD", "#D4A5A5", "#9B59B6", "#3498DB",
        "#E67E22", "#2ECC71", "#F1C40F", "#E74C3C",
        "#1ABC9C", "#9B59B6", "#34495E", "#16A085",
        "#27AE60", "#2980B9", "#8E44AD", "#F39C12"
    ]
    player_colors = {player: colors[i % len(colors)] for i, player in enumerate(sorted(all_players))}
    
    # Calculate total games played for each player
    total_plays = {p: 0 for p in all_players}
    for game in games:
        for p in game:
            total_plays[p] = total_plays.get(p, 0) + 1
    
    # Show the last 20 games, reversed
    for i, game in enumerate(games[::-1][:20], 1):
        # Create colored player names with game count
        colored_players = [
            f'<span style="color: {player_colors[p]}; font-weight: bold;">{p} ({total_plays[p]})</span>'
            for p in game
        ]
        st.markdown(
            f"""
            <div style="
                background: #f8f9fa;
                border-radius: 8px;
                padding: 0.8em 1em;
                margin-bottom: 0.5em;
                font-size: 1.1em;">
                <span style="color: black; font-weight: normal;">Game {len(games) - i + 1}:</span> {' • '.join(colored_players)}
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.write("No games played yet.")

