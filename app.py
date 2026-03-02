import streamlit as st
import anthropic
import requests
import json

# ── Config ────────────────────────────────────────────────────────────────────
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG  = "https://image.tmdb.org/t/p/w500"

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Movie Night Picker",
    page_icon="🎬",
    layout="centered",
)

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
        "dark_mode": True,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── Load API keys from Streamlit secrets ──────────────────────────────────────
try:
    st.session_state.anthropic_key = st.secrets["ANTHROPIC_API_KEY"]
    st.session_state.tmdb_key      = st.secrets["TMDB_API_KEY"]
except Exception:
    # Fallback: prompt user manually (for local dev without secrets file)
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

# ── Theme colors ──────────────────────────────────────────────────────────────
dark = st.session_state.dark_mode

if dark:
    BG       = "#0f1117"
    SURFACE  = "#1c1f2e"
    BORDER   = "#2e3250"
    TEXT     = "#eef0f8"
    MUTED    = "#8b90b0"
    ACCENT   = "#7c9fff"
    ACCENT2  = "#ff8c69"
    BTN_TEXT = "#0f1117"
else:
    BG =       "#F5F6FA"
    SURFACE =  "#FFFFFF"
    BORDER =   "#D0D4E8"
    TEXT =     "#1A1D2E"
    MUTED =    "#5A5F7A"
    ACCENT =   "#3A5FD9"
    ACCENT2 =  "#C44B2B"
    BTN_TEXT = "#FFFFFF"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,700;1,400&family=Outfit:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'Outfit', sans-serif;
    background-color: {BG};
    color: {TEXT};
}}
.stApp {{ background-color: {BG}; }}
h1,h2,h3 {{ font-family: 'Fraunces', serif; }}

.hero-title {{
    font-family: 'Fraunces', serif;
    font-size: 2.8rem;
    font-weight: 700;
    color: {TEXT};
    line-height: 1.1;
    margin-bottom: 0.2rem;
}}
.hero-sub {{
    font-size: 1rem;
    color: {MUTED};
    font-weight: 300;
    margin-bottom: 0.5rem;
    letter-spacing: 0.03em;
}}
.step-indicator {{
    font-size: 0.72rem;
    color: {MUTED};
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin-bottom: 0.75rem;
}}
.question-label {{
    font-family: 'Fraunces', serif;
    font-style: italic;
    font-size: 1.3rem;
    color: {ACCENT};
    margin-bottom: 0.75rem;
    margin-top: 0.5rem;
}}
.movie-title-display {{
    font-family: 'Fraunces', serif;
    font-size: 1.9rem;
    font-weight: 700;
    color: {TEXT};
    margin-bottom: 0.2rem;
    line-height: 1.2;
}}
.movie-meta {{
    color: {MUTED};
    font-size: 0.82rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.9rem;
}}
.badge {{
    display: inline-block;
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 20px;
    padding: 0.2rem 0.8rem;
    font-size: 0.78rem;
    color: {MUTED};
    margin-right: 0.35rem;
    margin-bottom: 0.4rem;
}}
.rating-badge {{
    background: transparent;
    border: 1.5px solid {ACCENT2};
    color: {ACCENT2};
    font-weight: 600;
}}
.pitch-text {{
    font-size: 0.98rem;
    color: {TEXT};
    line-height: 1.8;
    border-left: 3px solid {ACCENT};
    padding: 1rem 1rem 1rem 1.2rem;
    margin-top: 1.25rem;
    font-style: italic;
    background: {SURFACE};
    border-radius: 0 8px 8px 0;
}}
.divider {{
    border: none;
    border-top: 1px solid {BORDER};
    margin: 1.75rem 0;
}}
.stButton > button {{
    background: {ACCENT} !important;
    color: {BTN_TEXT} !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    padding: 0.55rem 1.4rem !important;
    letter-spacing: 0.03em !important;
    transition: opacity 0.2s !important;
}}
.stButton > button:hover {{ opacity: 0.88 !important; }}
.stTextInput > div > div > input,
.stTextArea textarea {{
    background-color: {SURFACE} !important;
    border: 1.5px solid {BORDER} !important;
    color: {TEXT} !important;
    border-radius: 8px !important;
    font-family: 'Outfit', sans-serif !important;
}}
.stTextInput > div > div > input:focus,
.stTextArea textarea:focus {{
    border-color: {ACCENT} !important;
    box-shadow: 0 0 0 2px {ACCENT}33 !important;
}}
div[data-testid="stRadio"] label {{ color: {TEXT} !important; }}
.picks-label {{
    font-size: 0.72rem;
    color: {MUTED};
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin-bottom: 1rem;
}}
</style>
""", unsafe_allow_html=True)


# ── API helpers ────────────────────────────────────────────────────────────────
def get_movie_candidates(profile: dict) -> list[str]:
    """LLM Call #1 — Claude picks 5 movie titles as JSON."""
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
    return json.loads(message.content[0].text.strip())


def tmdb_search(title: str) -> dict | None:
    """Search TMDB for a title and return enriched movie data."""
    r = requests.get(f"{TMDB_BASE}/search/movie",
                     params={"api_key": st.session_state.tmdb_key, "query": title, "page": 1})
    results = r.json().get("results", [])
    if not results:
        return None
    details = requests.get(f"{TMDB_BASE}/movie/{results[0]['id']}",
                           params={"api_key": st.session_state.tmdb_key}).json()
    return {
        "title":      details.get("title", title),
        "year":       details.get("release_date", "")[:4],
        "rating":     round(details.get("vote_average", 0), 1),
        "runtime":    details.get("runtime", "?"),
        "genres":     [g["name"] for g in details.get("genres", [])[:3]],
        "overview":   details.get("overview", ""),
        "poster_url": TMDB_IMG + details["poster_path"] if details.get("poster_path") else None,
    }


def generate_pitch(profile: dict, movie: dict) -> str:
    """LLM Call #2 — Claude writes a warm, personalized pitch."""
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
     "text",   None,
     "e.g. tired and cozy, hyped and energetic, emotionally drained…"),

    ("watching_with", "Who's joining you?",
     "select", ["Just me 🙋", "Date night 💑", "Friends 🍻", "Family / kids 👨‍👩‍👧"],
     None),

    ("genres",        "Any genres you're craving — or want to avoid?",
     "text",   None,
     "e.g. I love thrillers, please no horror or musicals"),

    ("runtime",       "How long do you want the movie to be?",
     "select", ["No preference", "Under 90 min", "90–120 min", "120+ min is fine"],
     None),

    ("recent",        "Anything you've watched recently? Loved it or hated it?",
     "text",   None,
     "e.g. Loved Oppenheimer, couldn't get through The Notebook"),
]


# ── Header row ────────────────────────────────────────────────────────────────
col_title, col_toggle = st.columns([5, 1])
with col_title:
    st.markdown('<div class="hero-title">🎬 Movie Night Picker</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Answer five quick questions. Get your perfect film.</div>',
                unsafe_allow_html=True)
with col_toggle:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("☀️" if dark else "🌙", key="theme_toggle"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

st.markdown('<hr class="divider">', unsafe_allow_html=True)


# ── Intake questions ───────────────────────────────────────────────────────────
if not st.session_state.done:
    step = st.session_state.step

    if step < len(QUESTIONS):
        key, question, qtype, options, placeholder = QUESTIONS[step]

        st.markdown(f'<div class="step-indicator">Question {step+1} of {len(QUESTIONS)}</div>',
                    unsafe_allow_html=True)
        st.progress(step / len(QUESTIONS))
        st.markdown(f'<div class="question-label">{question}</div>', unsafe_allow_html=True)

        if qtype == "text":
            # Wrap in st.form so pressing Enter submits
            with st.form(key=f"form_{step}"):
                answer    = st.text_input("", placeholder=placeholder,
                                          label_visibility="collapsed")
                submitted = st.form_submit_button("Next →")
            if submitted:
                if answer.strip():
                    st.session_state.profile[key] = answer.strip()
                    st.session_state.step += 1
                    st.rerun()
                else:
                    st.warning("Please type something first!")

        elif qtype == "select":
            with st.form(key=f"form_{step}"):
                answer    = st.radio("", options, label_visibility="collapsed")
                submitted = st.form_submit_button("Next →")
            if submitted:
                st.session_state.profile[key] = answer
                st.session_state.step += 1
                st.rerun()

        # ── Back button (shown from step 1 onward) ─────────────────────────
        if step > 0:
            if st.button("← Back", key=f"back_{step}"):
                st.session_state.step -= 1
                st.session_state.profile.pop(key, None)
                st.rerun()

    else:
        # All answers collected — run pipeline
        st.progress(1.0)
        with st.spinner("Curating your perfect movie…"):
            try:
                titles     = get_movie_candidates(st.session_state.profile)
                candidates = [d for t in titles if (d := tmdb_search(t))]

                if not candidates:
                    st.error("Couldn't find movies on TMDB. Try again!")
                    st.stop()

                pitch = generate_pitch(st.session_state.profile, candidates[0])

                st.session_state.candidates      = candidates
                st.session_state.candidate_index = 0
                st.session_state.movie_data      = candidates[0]
                st.session_state.pitch           = pitch
                st.session_state.done            = True
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

    st.markdown(f'<div class="picks-label">Tonight\'s pick · {idx+1} of {total}</div>',
                unsafe_allow_html=True)

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

        badges = f'<span class="badge rating-badge">⭐ {movie["rating"]}</span>'
        for g in movie["genres"]:
            badges += f'<span class="badge">{g}</span>'
        st.markdown(badges, unsafe_allow_html=True)
        st.markdown(f'<div class="pitch-text">{pitch}</div>', unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if idx + 1 < total:
            if st.button("🔄 Next pick"):
                next_movie = st.session_state.candidates[idx + 1]
                with st.spinner("Writing your pitch…"):
                    pitch = generate_pitch(st.session_state.profile, next_movie)
                st.session_state.candidate_index += 1
                st.session_state.movie_data       = next_movie
                st.session_state.pitch            = pitch
                st.rerun()
        else:
            st.caption("No more picks!")

    with col_b:
        if st.button("← Change answers"):
            st.session_state.done        = False
            st.session_state.step        = len(QUESTIONS) - 1
            st.session_state.candidates  = []
            st.session_state.movie_data  = None
            st.session_state.pitch       = None
            st.rerun()

    with col_c:
        if st.button("↩ Start over"):
            for k in ["step", "profile", "candidates", "candidate_index",
                      "movie_data", "pitch", "done"]:
                del st.session_state[k]
            st.rerun()
