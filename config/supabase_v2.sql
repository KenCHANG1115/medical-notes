-- V2: Multi-user highlights and right-sidebar annotations
-- Run this in Supabase Dashboard > SQL Editor

-- Drop old tables
DROP TABLE IF EXISTS highlights;
DROP TABLE IF EXISTS annotations;

-- Highlights: each row = one highlighted text span
CREATE TABLE highlights (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  note_id TEXT NOT NULL,
  section_idx INT NOT NULL,
  anchor_text TEXT NOT NULL,
  anchor_prefix TEXT NOT NULL DEFAULT '',
  anchor_suffix TEXT NOT NULL DEFAULT '',
  color TEXT NOT NULL DEFAULT 'yellow',
  user_name TEXT NOT NULL DEFAULT 'Anonymous',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Annotations: right-sidebar comments linked to specific text
CREATE TABLE annotations (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  note_id TEXT NOT NULL,
  section_idx INT NOT NULL,
  anchor_text TEXT NOT NULL,
  anchor_prefix TEXT NOT NULL DEFAULT '',
  anchor_suffix TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL DEFAULT '',
  user_name TEXT NOT NULL DEFAULT 'Anonymous',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE highlights ENABLE ROW LEVEL SECURITY;
ALTER TABLE annotations ENABLE ROW LEVEL SECURITY;

-- Allow anonymous read/write (shared study tool)
CREATE POLICY "Allow all highlights" ON highlights FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all annotations" ON annotations FOR ALL USING (true) WITH CHECK (true);

-- Indexes
CREATE INDEX idx_hl_note ON highlights(note_id);
CREATE INDEX idx_ann_note ON annotations(note_id);
