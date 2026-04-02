import streamlit as st
import pandas as pd
import json
import ast
import requests
import heapq
import urllib.parse
from datetime import datetime

# =========================
# SAFE PARSER (ADDED)
# =========================
def safe_parse(text):
    try:
        return json.loads(text)
    except:
        try:
            return ast.literal_eval(text)
        except:
            return []

# Set page config
st.set_page_config(page_title="CineMatch AI", layout="wide", page_icon="🍿")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #e4efe9 0%, #93a5ce 100%);
        background-attachment: fixed;
    }
    
    [data-testid="stHeader"] {
        background-color: transparent;
    }

    .stApp {
        color: #1e293b;
    }
    
    h1 {
        text-align: center;
        background: linear-gradient(to right, #ff416c, #ff4b2b, #f53844, #42378f);
        background-size: 300% 300%;
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 4.5rem !important;
        margin-bottom: 0px;
        animation: gradientShift 5s ease infinite;
        text-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    p.subtitle {
        text-align: center;
        color: #334155;
        font-size: 1.3rem;
        margin-bottom: 3.5rem;
        font-weight: 400;
        letter-spacing: 1px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1>🍿 CineMatch AI</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Discover your next favorite movie</p>', unsafe_allow_html=True)

@st.cache_data
def fetch_poster_url(movie_id, title):
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key=8265bd1679663a7ea12ac168da84d2e8&language=en-US"
        data = requests.get(url, timeout=5).json()
        poster_path = data.get('poster_path')
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500{poster_path}"
    except:
        pass
        
    clean_title = urllib.parse.quote(title)
    return f"https://ui-avatars.com/api/?name={clean_title}&background=334155&color=fff&size=500"


@st.cache_data
def load_data():
    # ✅ FIXED (NaN handled)
    df = pd.read_csv('data/movies.csv').fillna('')

    movies_data = []

    for index, row in df.iterrows():
        if pd.isna(row['title']):
            continue
        
        year = ""
        rd = str(row.get('release_date', ''))
        if len(rd) >= 4 and rd[:4].isdigit():
            year = rd[:4]
            
        # ✅ FIXED GENRES
        genres_data = safe_parse(row.get('genres', '[]'))
        genres = [g['name'] for g in genres_data if isinstance(g, dict) and 'name' in g]

        # ✅ FIXED KEYWORDS
        keywords_data = safe_parse(row.get('keywords', '[]'))
        keywords = [k['name'] for k in keywords_data if isinstance(k, dict) and 'name' in k]
                
        movies_data.append({
            'id': row['id'],
            'title': str(row['title']).strip(),
            'genres': genres,
            'keywords': keywords,
            'year': year
        })
    
    graph = {}
    movies_dict = {m['title']: m for m in movies_data}
    
    for m in movies_dict.keys():
        graph[m] = []
        
    genre_to_movies = {}
    keyword_to_movies = {}

    for m in movies_data:
        for g in m['genres']:
            genre_to_movies.setdefault(g, []).append(m['title'])
        for k in m['keywords']:
            keyword_to_movies.setdefault(k, []).append(m['title'])

    for m in movies_data:
        title = m['title']
        connected_counts = {}
        
        for k in m['keywords']:
            for other in keyword_to_movies[k]:
                if other != title:
                    connected_counts[other] = connected_counts.get(other, 0) + 2
                    
        for g in m['genres']:
            for other in genre_to_movies[g]:
                if other != title:
                    connected_counts[other] = connected_counts.get(other, 0) + 1
        
        for other, weight in connected_counts.items():
            if weight >= 2:
                cost = max(1, 10 - weight)
                graph[title].append({'node': other, 'cost': cost})
                
    return movies_dict, list(movies_dict.keys()), graph

movies_dict, movie_names, graph = load_data()

# =========================
# RECOMMENDATION
# =========================
def ucs_recommendation(start_node, limit=12):
    if start_node not in graph:
        return []
    frontier = []
    heapq.heappush(frontier, (0, start_node))
    recommendations = []
    visited = set()
    
    while frontier and len(recommendations) < limit:
        current_cost, current_node = heapq.heappop(frontier)
        if current_node in visited:
            continue
        visited.add(current_node)
        
        if current_node != start_node:
            recommendations.append(current_node)
            
        for edge in graph[current_node]:
            heapq.heappush(frontier, (current_cost + edge['cost'], edge['node']))
    return recommendations


selected_movie = st.selectbox("Select a Movie you like:", movie_names[:2000])

find_button = st.button("Find Recommendations 🚀", use_container_width=True)

if find_button:
    recs = ucs_recommendation(selected_movie)
        
    if not recs:
        st.warning("No connections found for this movie.")
    else:
        st.markdown(f"## ✨ Recommendations for **{selected_movie}**")
        
        cols = st.columns(4)
        for idx, rec in enumerate(recs):
            m_data = movies_dict[rec]
            poster_url = fetch_poster_url(m_data['id'], m_data['title'])
            
            with cols[idx % 4]:
                st.image(poster_url)
                st.write(m_data['title'])
