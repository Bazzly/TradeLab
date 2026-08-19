import streamlit as st

from lib.content.lessons import LESSONS

st.set_page_config(page_title="TradeLab — Learning", page_icon="🎓", layout="wide")

st.title("Learning")
st.caption(
    "Beginner curriculum, v1: the concepts TradeLab's engines are actually built on. "
    "Progress tracking is session-only for now — persistent tracking ships once the "
    "database is wired up."
)

if "completed_lessons" not in st.session_state:
    st.session_state.completed_lessons = set()

titles = [lesson.title for lesson in LESSONS]
selected_title = st.sidebar.radio("Lessons", titles)
lesson = next(lesson for lesson in LESSONS if lesson.title == selected_title)

st.header(lesson.title)
st.caption(lesson.summary)
st.markdown(lesson.body)

st.divider()

is_done = lesson.id in st.session_state.completed_lessons
done = st.checkbox("Mark as read", value=is_done, key=f"done_{lesson.id}")
if done:
    st.session_state.completed_lessons.add(lesson.id)
else:
    st.session_state.completed_lessons.discard(lesson.id)

progress = len(st.session_state.completed_lessons) / len(LESSONS)
st.progress(progress, text=f"{len(st.session_state.completed_lessons)}/{len(LESSONS)} lessons read this session")
