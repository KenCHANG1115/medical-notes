-- Supabase tables for Medical Notes highlights and annotations
-- Run this in Supabase Dashboard > SQL Editor

-- Highlights table (stores per-note highlight data)
CREATE TABLE IF NOT EXISTS highlights (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  note_id TEXT NOT NULL UNIQUE,
  data JSONB NOT NULL DEFAULT '[]',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Annotations table (stores per-section margin notes)
CREATE TABLE IF NOT EXISTS annotations (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  note_id TEXT NOT NULL,
  section TEXT NOT NULL,
  text TEXT NOT NULL DEFAULT '',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(note_id, section)
);

-- Enable Row Level Security
ALTER TABLE highlights ENABLE ROW LEVEL SECURITY;
ALTER TABLE annotations ENABLE ROW LEVEL SECURITY;

-- Allow anonymous read/write (since this is a personal study tool)
CREATE POLICY "Allow all access to highlights"
  ON highlights FOR ALL
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow all access to annotations"
  ON annotations FOR ALL
  USING (true)
  WITH CHECK (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_highlights_note_id ON highlights(note_id);
CREATE INDEX IF NOT EXISTS idx_annotations_note_id ON annotations(note_id);
CREATE INDEX IF NOT EXISTS idx_annotations_lookup ON annotations(note_id, section);
