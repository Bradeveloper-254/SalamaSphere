# Wearable audio transfer verification

1. Confirm the configured I2S pins produce a non-empty `/sos_latest.wav`.
2. Trigger the SOS button and verify the event JSON contains `event_id`,
   `device_identifier`, `event_type`, and `recording_status`.
3. Verify metadata reports `available:true`, `mime_type:audio/wav`, and a
   positive byte count.
4. Connect the Flutter app and verify it sends `GET:<event_id>`.
5. Verify the wearable sends all audio-data notifications and ends with a
   `complete` recording status.
6. Verify the app stores the bytes, creates the Django incident, uploads the
   multipart file, and can play the recording from the victim dashboard.
