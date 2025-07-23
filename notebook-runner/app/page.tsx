'use client';

import React, { useRef, useState } from 'react';

// Set this to your HuggingFace Space backend URL
const API_BASE = 'https://aditya203-backend_final.hf.space';

type Notebook = 1 | 2;

export default function Page() {
  const [notebook, setNotebook] = useState<Notebook | null>(null);
  const [inputMode, setInputMode] = useState<'pdf' | 'url'>('pdf');
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [url, setUrl] = useState('');
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [transcribedText, setTranscribedText] = useState('');
  const [finalResponse, setFinalResponse] = useState('');
  const [sources, setSources] = useState<string[]>([]);
  const [audioReplyUrl, setAudioReplyUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  // Start recording
  const startRecording = async () => {
    setTranscribedText('');
    setFinalResponse('');
    setSources([]);
    setAudioReplyUrl(null);

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    const chunks: BlobPart[] = [];
    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = () => {
      const blob = new Blob(chunks, { type: 'audio/webm' });
      setAudioBlob(blob);
    };
    recorder.start();
    setMediaRecorder(recorder);
    setIsRecording(true);
  };

  // Stop recording
  const stopRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  // Handle submit
  const handleSubmit = async () => {
    alert('Submit clicked!');
    if (!notebook) {
      alert('Please select a notebook.');
      return;
    }
    if (inputMode === 'pdf' && !pdfFile) {
      alert('Please upload a PDF file.');
      return;
    }
    if (inputMode === 'url' && !url) {
      alert('Please enter a URL.');
      return;
    }
    if (!audioBlob) {
      alert('Please record your question.');
      return;
    }

    setLoading(true);
    setTranscribedText('');
    setFinalResponse('');
    setSources([]);
    setAudioReplyUrl(null);

    const formData = new FormData();
    formData.append('input_mode', inputMode);
    if (inputMode === 'pdf' && pdfFile) formData.append('pdf', pdfFile);
    if (inputMode === 'url') formData.append('url', url);
    // Convert audio to .wav or .mp3 as needed
    const audioFile = new File([audioBlob], notebook === 1 ? 'audio.wav' : 'audio.mp3', {
      type: notebook === 1 ? 'audio/wav' : 'audio/mp3',
    });
    formData.append('audio', audioFile);

    const endpoint =
      notebook === 1 ? '/api/run-notebook-1' : '/api/run-notebook-2';

    try {
      alert('About to send request!');
      const res = await fetch(API_BASE + endpoint, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (data.error) {
        alert(data.error);
        setLoading(false);
        return;
      }
      setTranscribedText(data.transcribed_text || '');
      setFinalResponse(data.final_response || '');
      setSources(data.sources || []);
      // Fetch and play audio reply if available
      if (data.audio_reply_path) {
        // Try to fetch the audio file from backend
        const audioUrl = API_BASE + '/static/' + data.audio_reply_path.replace(/^.*[\\/]/, '');
        setAudioReplyUrl(audioUrl);
      }
    } catch (err) {
      alert('Error communicating with backend.');
    }
    setLoading(false);
  };

  return (
    <div style={{ maxWidth: 600, margin: '40px auto', fontFamily: 'sans-serif' }}>
      <h2>Notebook Runner</h2>
      <div style={{ marginBottom: 16 }}>
        <button
          onClick={() => setNotebook(1)}
          style={{
            background: notebook === 1 ? '#0070f3' : '#eee',
            color: notebook === 1 ? '#fff' : '#000',
            marginRight: 8,
            padding: '8px 16px',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
          }}
        >
          Enable Notebook 1
        </button>
        <button
          onClick={() => setNotebook(2)}
          style={{
            background: notebook === 2 ? '#0070f3' : '#eee',
            color: notebook === 2 ? '#fff' : '#000',
            padding: '8px 16px',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
          }}
        >
          Enable Notebook 2
        </button>
      </div>
      <div style={{ marginBottom: 16 }}>
        <label>
          <input
            type="radio"
            checked={inputMode === 'pdf'}
            onChange={() => setInputMode('pdf')}
          />
          PDF
        </label>
        <label style={{ marginLeft: 16 }}>
          <input
            type="radio"
            checked={inputMode === 'url'}
            onChange={() => setInputMode('url')}
          />
          URL
        </label>
      </div>
      {inputMode === 'pdf' ? (
        <div style={{ marginBottom: 16 }}>
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
          />
        </div>
      ) : (
        <div style={{ marginBottom: 16 }}>
          <input
            type="text"
            placeholder="Enter URL"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            style={{ width: '100%', padding: 8 }}
          />
        </div>
      )}
      <div style={{ marginBottom: 16 }}>
        {!isRecording ? (
          <button onClick={startRecording} style={{ padding: '8px 16px' }}>
            Start Recording
          </button>
        ) : (
          <button onClick={stopRecording} style={{ padding: '8px 16px', background: '#f33', color: '#fff' }}>
            Stop Recording
          </button>
        )}
        {audioBlob && (
          <audio
            controls
            src={URL.createObjectURL(audioBlob)}
            style={{ display: 'block', marginTop: 8 }}
          />
        )}
      </div>
      <div>
        <button
          onClick={handleSubmit}
          disabled={loading}
          style={{
            padding: '10px 24px',
            background: '#28a745',
            color: '#fff',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
            fontWeight: 'bold',
          }}
        >
          {loading ? 'Processing...' : 'Submit'}
        </button>
      </div>
      <hr style={{ margin: '32px 0' }} />
      {transcribedText && (
        <div>
          <strong>Transcribed Text:</strong>
          <div style={{ background: '#f6f8fa', padding: 8, borderRadius: 4 }}>{transcribedText}</div>
        </div>
      )}
      {finalResponse && (
        <div style={{ marginTop: 16 }}>
          <strong>Final Response:</strong>
          <div style={{ background: '#f6f8fa', padding: 8, borderRadius: 4 }}>{finalResponse}</div>
        </div>
      )}
      {sources.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <strong>Sources:</strong>
          <ul>
            {sources.map((src, i) => (
              <li key={i}>{src}</li>
            ))}
          </ul>
        </div>
      )}
      {audioReplyUrl && (
        <div style={{ marginTop: 16 }}>
          <strong>Audio Reply:</strong>
          <audio ref={audioRef} controls src={audioReplyUrl} />
        </div>
      )}
    </div>
  );
}
