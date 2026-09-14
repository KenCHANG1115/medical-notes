-- V3: Image upload support for note sections
-- Run this in Supabase Dashboard > SQL Editor

-- Create storage bucket for note images (public read for display)
INSERT INTO storage.buckets (id, name, public)
VALUES ('note-images', 'note-images', true)
ON CONFLICT (id) DO NOTHING;

-- Allow anonymous uploads and reads on the bucket
CREATE POLICY "Allow public read note-images"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'note-images');

CREATE POLICY "Allow anonymous upload note-images"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'note-images');

CREATE POLICY "Allow anonymous delete note-images"
  ON storage.objects FOR DELETE
  USING (bucket_id = 'note-images');

-- Metadata table linking images to note sections
CREATE TABLE note_images (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  note_id TEXT NOT NULL,
  section_idx INT NOT NULL,
  storage_path TEXT NOT NULL,
  caption TEXT NOT NULL DEFAULT '',
  user_name TEXT NOT NULL DEFAULT 'Anonymous',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE note_images ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all note_images" ON note_images
  FOR ALL USING (true) WITH CHECK (true);

CREATE INDEX idx_ni_note ON note_images(note_id);
