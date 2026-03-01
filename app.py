# run in terminal:
# pip install -r requirements.txt
# then:
# streamlit run app.py
import streamlit as st
import anthropic
import requests
import json
import os

# ── Config ────────────────────────────────────────────────────────────────────
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG  = "https://image.tmdb.org/t/p/w500"

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Movie Night Picker",
    page_icon="🎬",
    layout="centered",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0d0d0d;
    color: #f0ece4;
}

.stApp { background-color: #0d0d0d; }

h1, h2, h3 { font-family: 'Playfair Display', serif; }

.hero-title {
    font-family: 'Playfair Display', serif;
    font-size: 3rem;
    font-weight: 700;
    color: #f0ece4;
    line-height: 1.1;
    margin-bottom: 0.2rem;
}
.hero-sub {
    font-family: 'DM Sans', sans-serif;
    font-size: 1rem;
    color: #888;
    font-weight: 300;
    margin-bottom: 2.5rem;
    letter-spacing: 0.04em;
}
.question-label {
    font-family: 'Playfair Display', serif;
    font-style: italic;
    font-size: 1.25rem;
    color: #c9a96e;
    margin-bottom: 0.5rem;
}
.step-indicator {
    font-size: 0.75rem;
    color: #555;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 1.5rem;
}
.movie-card {
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 16px;
    padding: 2rem;
    margin-top: 1rem;
}
.movie-title-display {
    font-family: 'Playfair Display', serif;
    font-size: 2rem;
    font-weight: 700;
    color: #f0ece4;
    margin-bottom: 0.25rem;
}
.movie-meta {
    color: #666;
    font-size: 0.85rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 1rem;
}
.badge {
    display: inline-block;
    background: #1e1e1e;
    border: 1px solid #333;
    border-radius: 20px;
    padding: 0.2rem 0.75rem;
    font-size: 0.78rem;
    color: #aaa;
    margin-right: 0.4rem;
    margin-bottom: 0.4rem;
}
.rating-badge {
    background: #1a1a0a;
    border: 1px solid #c9a96e;
    color: #c9a96e;
}
.pitch-text {
    font-size: 1rem;
    color: #ccc;
    line-height: 1.75;
    border-left: 2px solid #c9a96e;
    padding-left: 1rem;
    margin-top: 1.25rem;
    font-style: italic;
}
.divider {
    border: none;
    border-top: 1px solid #222;
    margin: 2rem 0;
}
/* Button styling */
.stButton > button {
    background: #c9a96e !important;
    color: #0d0d0d !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    padding: 0.6rem 1.5rem !important;
    letter-spacing: 0.04em !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

.stTextInput > div > div > input,
.stSelectbox > div > div,
.stTextArea textarea {
    background-color: #161616 !important;
    border: 1px solid #2a2a2a !important;
    color: #f0ece4 !important;
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)


# ── Session state init ────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "step": 0,
        "profile": {},
        "candidates": [],
        "candidate_index": 0,
        "movie_data": None,
        "pitch": None,
        "done": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ── API helpers ────────────────────────────────────────────────────────────────
def get_movie_candidates(profile: dict, tmdb_key: str) -> list[dict]:
    """LLM Call #1 — Claude picks movie titles based on user profile."""
    client = anthropic.Anthropic(api_key=st.session_state.anthropic_key)
    prompt = f"""You are a brilliant film curator. Based on this viewer profile, suggest exactly 5 movies.

VIEWER PROFILE:
- Mood: {profile.get('mood')}
- Watching with: {profile.get('watching_with')}
- Genre preferences: {profile.get('genres')}
- Max runtime: {profile.get('runtime')}
- Recent watches: {profile.get('recent')}

Return ONLY a JSON array of 5 movie titles, ordered best-to-worst fit. Example:
["Movie Title 1", "Movie Title 2", "Movie Title 3", "Movie Title 4", "Movie Title 5"]

No explanation. Just the JSON array."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = message.content[0].text.strip()
    titles = json.loads(raw)
    return titles


def tmdb_search(title: str, tmdb_key: str) -> dict | None:
    """Search TMDB for a title and return enriched movie data."""
    r = requests.get(f"{TMDB_BASE}/search/movie",
                     params={"api_key": tmdb_key, "query": title, "page": 1})
    results = r.json().get("results", [])
    if not results:
        return None
    movie = results[0]
    # Fetch full details for runtime
    details = requests.get(f"{TMDB_BASE}/movie/{movie['id']}",
                           params={"api_key": tmdb_key}).json()
    return {
        "title": details.get("title", title),
        "year": details.get("release_date", "")[:4],
        "rating": round(details.get("vote_average", 0), 1),
        "runtime": details.get("runtime", "?"),
        "genres": [g["name"] for g in details.get("genres", [])[:3]],
        "overview": details.get("overview", ""),
        "poster_url": TMDB_IMG + details["poster_path"] if details.get("poster_path") else None,
    }


def generate_pitch(profile: dict, movie: dict) -> str:
    """LLM Call #2 — Claude writes a personalized pitch for the chosen movie."""
    client = anthropic.Anthropic(api_key=st.session_state.anthropic_key)
    prompt = f"""You are a warm, witty film friend writing a short personalized recommendation.

VIEWER PROFILE:
- Mood: {profile.get('mood')}
- Watching with: {profile.get('watching_with')}
- Genres they like/dislike: {profile.get('genres')}
- Recent watches they mentioned: {profile.get('recent')}

MOVIE:
- Title: {movie['title']} ({movie['year']})
- Genres: {', '.join(movie['genres'])}
- Overview: {movie['overview']}

Write 2-3 sentences explaining why THIS person will love THIS movie TONIGHT. 
Be specific — reference their mood and who they're watching with. 
Sound like a friend, not a reviewer. No spoilers."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()


# ── Questions ──────────────────────────────────────────────────────────────────
QUESTIONS = [
    ("mood",          "How are you feeling tonight?",
     "text", None,
     "e.g. tired and cozy, hyped and energetic, emotionally drained…"),

    ("watching_with", "Who's joining you?",
     "select", ["Just me 🙋", "Date night 💑", "Friends 🍻", "Family / kids 👨‍👩‍👧"],
     None),

    ("genres",        "Any genres you're craving — or want to avoid?",
     "text", None,
     "e.g. I love thrillers, please no horror or musicals"),

    ("runtime",       "How long do you want the movie to be?",
     "select", ["No preference", "Under 90 min", "90–120 min", "120+ min is fine"],
     None),

    ("recent",        "Anything you've watched recently? Loved it or hated it?",
     "text", None,
     "e.g. Loved Oppenheimer, couldn't get through The Notebook"),
]


# ── UI ─────────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">🎬 Movie Night Picker</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Answer five quick questions. Get your perfect film.</div>', unsafe_allow_html=True)

# ── API key gate ───────────────────────────────────────────────────────────────
if "anthropic_key" not in st.session_state or "tmdb_key" not in st.session_state:
    with st.form("keys_form"):
        st.markdown("**Enter your API keys to get started**")
        ak = st.text_input("Anthropic API Key", type="password")
        tk = st.text_input("TMDB API Key", type="password",
                           help="Free at themoviedb.org — Settings → API")
        submitted = st.form_submit_button("Let's go →")
        if submitted:
            if ak and tk:
                st.session_state.anthropic_key = ak
                st.session_state.tmdb_key = tk
                st.rerun()
            else:
                st.error("Both keys are required.")
    st.stop()

# ── Intake questions ───────────────────────────────────────────────────────────
if not st.session_state.done:
    step = st.session_state.step

    if step < len(QUESTIONS):
        key, question, qtype, options, placeholder = QUESTIONS[step]

        # Progress
        st.markdown(f'<div class="step-indicator">Question {step+1} of {len(QUESTIONS)}</div>',
                    unsafe_allow_html=True)
        progress = (step) / len(QUESTIONS)
        st.progress(progress)

        st.markdown(f'<div class="question-label">{question}</div>', unsafe_allow_html=True)

        if qtype == "text":
            answer = st.text_input("", placeholder=placeholder, key=f"input_{step}",
                                   label_visibility="collapsed")
            if st.button("Next →", key=f"btn_{step}"):
                if answer.strip():
                    st.session_state.profile[key] = answer.strip()
                    st.session_state.step += 1
                    st.rerun()
                else:
                    st.warning("Please type something first!")

        elif qtype == "select":
            answer = st.radio("", options, key=f"input_{step}", label_visibility="collapsed")
            if st.button("Next →", key=f"btn_{step}"):
                st.session_state.profile[key] = answer
                st.session_state.step += 1
                st.rerun()

    else:
        # All questions answered — run the pipeline
        st.progress(1.0)
        with st.spinner("Curating your perfect movie…"):
            try:
                titles = get_movie_candidates(
                    st.session_state.profile, st.session_state.tmdb_key)

                candidates = []
                for t in titles:
                    data = tmdb_search(t, st.session_state.tmdb_key)
                    if data:
                        candidates.append(data)

                if not candidates:
                    st.error("Couldn't find movies on TMDB. Try again!")
                    st.stop()

                st.session_state.candidates = candidates
                st.session_state.candidate_index = 0

                # Generate pitch for first candidate
                pitch = generate_pitch(st.session_state.profile, candidates[0])
                st.session_state.pitch = pitch
                st.session_state.movie_data = candidates[0]
                st.session_state.done = True
                st.rerun()

            except json.JSONDecodeError:
                st.error("Claude returned unexpected data. Please try again.")
            except Exception as e:
                st.error(f"Something went wrong: {e}")

# ── Results ────────────────────────────────────────────────────────────────────
if st.session_state.done and st.session_state.movie_data:
    movie = st.session_state.movie_data
    pitch = st.session_state.pitch
    idx   = st.session_state.candidate_index
    total = len(st.session_state.candidates)

    st.markdown(f'<div class="step-indicator">Tonight\'s pick {idx+1} of {total}</div>',
                unsafe_allow_html=True)

    with st.container():
        col1, col2 = st.columns([1, 2], gap="large")

        with col1:
            if movie["poster_url"]:
                st.image(movie["poster_url"], use_container_width=True)
            else:
                st.markdown("🎬")

        with col2:
            st.markdown(f'<div class="movie-title-display">{movie["title"]}</div>',
                        unsafe_allow_html=True)
            st.markdown(
                f'<div class="movie-meta">{movie["year"]} &nbsp;·&nbsp; {movie["runtime"]} min</div>',
                unsafe_allow_html=True)

            # Badges
            badges = ""
            badges += f'<span class="badge rating-badge">⭐ {movie["rating"]}</span>'
            for g in movie["genres"]:
                badges += f'<span class="badge">{g}</span>'
            st.markdown(badges, unsafe_allow_html=True)

            st.markdown(f'<div class="pitch-text">{pitch}</div>', unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        if idx + 1 < total:
            if st.button("🔄 Try next pick"):
                next_idx = idx + 1
                next_movie = st.session_state.candidates[next_idx]
                with st.spinner("Writing your pitch…"):
                    pitch = generate_pitch(st.session_state.profile, next_movie)
                st.session_state.candidate_index = next_idx
                st.session_state.movie_data = next_movie
                st.session_state.pitch = pitch
                st.rerun()
        else:
            st.markdown('<span style="color:#555;font-size:0.85rem">No more picks!</span>',
                        unsafe_allow_html=True)
    with col_b:
        if st.button("↩ Start over"):
            for k in ["step","profile","candidates","candidate_index",
                      "movie_data","pitch","done"]:
                del st.session_state[k]
            st.rerun()
