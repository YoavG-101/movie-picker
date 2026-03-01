:clapper: Movie Night Picker

What it does: A chatbot that recommends the perfect movie for your night. It asks a few quick questions (your mood, who you're watching with, genre preferences, and how much time you have), then returns a personalized pick with a poster image and a custom "why you'll love this tonight" blurb.

Data source: TMDB API (free) for live movie data including titles, genres, ratings, and poster images.

Tech stack:
• Python + Streamlit (UI)
• Whatever free LLM API (personalized recommendations + pitch writing)
• TMDB API (movie knowledge + posters)
• Two LLM calls chained: one to match movies to the user's profile, one to write the personalized pitch

End result: A clean Streamlit web app where users answer a short conversational intake, then get a movie card with a poster, rating, and a paragraph written specifically for them explaining why this movie fits their exact mood tonight.

Bonus features in scope (from Dan's list): Multimodal poster display, LLM chaining, conversational UI.
