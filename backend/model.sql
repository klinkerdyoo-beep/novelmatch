

-- ตารางเก่า
-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.users (
  id integer NOT NULL DEFAULT nextval('users_id_seq'::regclass),
  username character varying NOT NULL,
  email character varying NOT NULL,
  password character varying NOT NULL,
  CONSTRAINT users_pkey PRIMARY KEY (id)
);
CREATE TABLE public.comparison_novels (
  id integer NOT NULL DEFAULT nextval('novels_id_seq'::regclass),
  title character varying NOT NULL,
  synopsis text,
  author character varying,
  genre json,
  book_cover text,
  CONSTRAINT comparison_novels_pkey PRIMARY KEY (id)
);
CREATE TABLE public.user_preferences (
  id integer NOT NULL DEFAULT nextval('user_preferences_id_seq'::regclass),
  user_id integer NOT NULL,
  enjoyed_character json NOT NULL,
  disliked_character text NOT NULL,
  liked_character text,
  enjoyed_story json NOT NULL,
  disliked_story json NOT NULL,
  enjoyed_genres json NOT NULL,
  disliked_genres json NOT NULL,
  CONSTRAINT user_preferences_pkey PRIMARY KEY (id),
  CONSTRAINT fk_user_preferences_user FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.match_history (
  id integer NOT NULL DEFAULT nextval('analyst_id_seq'::regclass),
  user_id integer NOT NULL,
  novel_id integer NOT NULL,
  score integer,
  matches json,
  mismatches json,
  limitations json,
  matches_level character varying,
  data_sources json,
  review_summary json,
  review_overview text,
  review_sources json,
  matches_summary text,
  CONSTRAINT match_history_pkey PRIMARY KEY (id),
  CONSTRAINT fk_analyst_user FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT fk_analyst_novel FOREIGN KEY (novel_id) REFERENCES public.comparison_novels(id)
);