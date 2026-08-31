'use client';

import { useEffect, useState } from 'react';

type Meeting = {
  id: string;
  title: string;
  status: 'live' | 'completed' | 'scheduled';
  participants?: number;
  duration: string;
  summary?: string;
  sentiment?: string;
  tokens_used?: string | number;
  processing_time?: string;
  step_timings?: string;
};

export default function Dashboard() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [botUrl, setBotUrl] = useState('');
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [dispatchStatus, setDispatchStatus] = useState('');
  const [uploadStatus, setUploadStatus] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    const fetchMeetings = async () => {
      try {
        const res = await fetch('/api/meetings');
        if (res.ok) {
          const data = await res.json();
          setMeetings(data);
        }
      } catch (e) {
        console.error('Failed to fetch meetings', e);
      } finally {
        setLoading(false);
      }
    };
    fetchMeetings();
    const intervalId = setInterval(fetchMeetings, 3000);
    return () => clearInterval(intervalId);
  }, []);

  const handleDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!botUrl) return;
    setDispatchStatus('Dispatching...');
    try {
      const res = await fetch('/api/dispatch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: botUrl }),
      });
      if (res.ok) {
        setDispatchStatus('AI Notetaker Dispatched!');
        setBotUrl('');
      } else {
        const errorText = await res.text();
        setDispatchStatus('Error ' + res.status + ': ' + errorText.substring(0, 50));
      }
    } catch (e) {
      setDispatchStatus('Backend unreachable: ' + e);
    }
    setTimeout(() => setDispatchStatus(''), 5000);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setIsUploading(true);
    setUploadStatus('Preparing upload...');
        const chunkSize = 2 * 1024 * 1024; // 2MB chunks for max compatibility and stability across any reverse proxy
        const totalChunks = Math.ceil(file.size / chunkSize);
        const fileId = Date.now() + '-' + file.name.replace(/[^a-zA-Z0-9.-]/g, '_');
        try {
            for (let i = 0; i < totalChunks; i++) {
                const start = i * chunkSize;
                const end = Math.min(start + chunkSize, file.size);
                const chunkData = file.slice(start, end);
                setUploadStatus('Uploading chunk ' + (i + 1) + ' of ' + totalChunks + '...');
                const formData = new FormData();
                formData.append('chunk', chunkData, file.name);
        formData.append('file_id', fileId);
        formData.append('chunk_index', String(i));
        formData.append('total_chunks', String(totalChunks));
        formData.append('filename', file.name);
        const res = await fetch('/api/upload-chunk', { method: 'POST', body: formData });
        if (!res.ok) {
          const errText = await res.text();
          setUploadStatus('Upload failed on chunk ' + (i + 1) + ': ' + errText.substring(0, 80));
          setIsUploading(false);
          return;
        }
      }
      setUploadStatus('Upload complete! Processing...');
    } catch (err) {
      setUploadStatus('Upload error: ' + err);
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  };

  const liveMeetings = meetings.filter((m) => m.status === 'live' || m.status === 'scheduled');
  const completedMeetings = meetings.filter((m) => m.status === 'completed');

  const getSentimentColor = (sentiment?: string) => {
    if (!sentiment) return 'text-neutral-400 bg-neutral-700/50';
    const s = sentiment.toLowerCase();
    if (s === 'positive') return 'text-emerald-400 bg-emerald-900/30';
    if (s === 'negative') return 'text-red-400 bg-red-900/30';
    if (s === 'processing') return 'text-yellow-400 bg-yellow-900/30';
    return 'text-blue-400 bg-blue-900/30';
  };

  return (
    <div className="min-h-screen bg-neutral-900 text-white">
      <nav className="border-b border-neutral-800 bg-neutral-900/95 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center text-sm font-bold">AI</div>
              <span className="font-semibold text-xl tracking-tight">Meeting Intelligence</span>
            </div>
            <div className="flex items-center gap-4">
              <button className="text-neutral-400 hover:text-white transition-colors">Settings</button>
              <div className="w-8 h-8 rounded-full overflow-hidden border-2 border-neutral-700">
                <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=CEO" alt="Profile" className="w-full h-full object-cover" />
              </div>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <section className="mb-12">
          <div className="bg-neutral-800/50 rounded-2xl border border-neutral-700/50 p-6 backdrop-blur-sm relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-purple-500 to-blue-500"></div>

            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 relative z-10">
              <div>
                <h2 className="text-2xl font-bold text-white mb-2">Send the AI Notetaker</h2>
                <p className="text-neutral-400">Paste your Microsoft Teams meeting link below, and the AI bot will automatically join as a guest.</p>
              </div>
              <form onSubmit={handleDispatch} className="flex flex-col md:flex-row w-full md:w-auto gap-3">
                <input
                  type="text"
                  value={botUrl}
                  onChange={(e) => setBotUrl(e.target.value)}
                  placeholder="https://teams.microsoft.com/l/meetup-join/..."
                  className="flex-1 md:w-80 bg-neutral-900 border border-neutral-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all placeholder:text-neutral-600"
                />
                <button
                  type="submit"
                  disabled={!botUrl || dispatchStatus === 'Dispatching...'}
                  className="bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white px-6 py-2 rounded-lg font-medium transition-colors whitespace-nowrap"
                >
                  Dispatch Teams Bot
                </button>
              </form>
            </div>
            {dispatchStatus && (
              <p className="mt-4 text-sm font-medium text-purple-400 animate-pulse">{dispatchStatus}</p>
            )}

            <div className="mt-6 pt-6 border-t border-neutral-700/50 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 relative z-10">
              <div>
                <h3 className="text-xl font-bold text-white mb-2">Transcribe YouTube Video</h3>
                <p className="text-neutral-400 text-sm">Paste a YouTube URL. The bot will download and transcribe it automatically.</p>
              </div>
              <form onSubmit={async (e) => {
                e.preventDefault();
                if (!youtubeUrl.includes('youtube') && !youtubeUrl.includes('youtu.be')) {
                  setDispatchStatus('Please enter a valid YouTube URL.');
                  return;
                }
                setDispatchStatus('Dispatching YouTube Bot...');
                try {
                  const res = await fetch('/api/youtube', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: youtubeUrl }),
                  });
                  if (res.ok) {
                    setDispatchStatus('YouTube Notetaker Dispatched!');
                    setYoutubeUrl('');
                  } else {
                    setDispatchStatus('Error ' + res.status);
                  }
                } catch {
                  setDispatchStatus('Backend unreachable');
                }
                setTimeout(() => setDispatchStatus(''), 5000);
              }} className="flex flex-col md:flex-row w-full md:w-auto gap-3">
                <input
                  type="text"
                  value={youtubeUrl}
                  onChange={(e) => setYoutubeUrl(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v=..."
                  className="flex-1 md:w-80 bg-neutral-900 border border-neutral-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-all placeholder:text-neutral-600"
                />
                <button
                  type="submit"
                  disabled={!youtubeUrl || dispatchStatus === 'Dispatching YouTube Bot...'}
                  className="bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white px-6 py-2 rounded-lg font-medium transition-colors whitespace-nowrap"
                >
                  Download and Transcribe YouTube
                </button>
              </form>
            </div>

            <div className="mt-6 pt-6 border-t border-neutral-700/50 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 relative z-10">
              <div>
                <h3 className="text-xl font-bold text-white mb-2">Upload Local Recording</h3>
                <p className="text-neutral-400 text-sm">Have a video or audio file? Upload it directly for AI transcription.</p>
              </div>
              <div className="flex flex-col items-end gap-2">
                <label className={"cursor-pointer bg-neutral-900 hover:bg-neutral-800 border border-neutral-700 text-white px-6 py-2 rounded-lg font-medium transition-all flex items-center gap-2 " + (isUploading ? 'opacity-50 pointer-events-none' : '')}>
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                  {isUploading ? 'Uploading...' : 'Select Video/Audio File'}
                  <input type="file" accept="video/*,audio/*" className="hidden" onChange={handleFileUpload} disabled={isUploading} />
                </label>
                {uploadStatus && <p className="text-sm text-neutral-400">{uploadStatus}</p>}
              </div>
            </div>

          </div>
        </section>

        <section>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-1">
              <h2 className="text-xl font-bold text-gray-300 mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse inline-block"></span>
                Active and Scheduled
              </h2>
              {loading ? (
                <div className="text-neutral-500 text-sm">Loading...</div>
              ) : liveMeetings.length === 0 ? (
                <div className="text-neutral-600 text-sm">No active meetings.</div>
              ) : (
                <div className="flex flex-col gap-4">
                  {liveMeetings.map((meeting) => (
                    <div key={meeting.id} className="bg-neutral-800/60 rounded-xl border border-neutral-700/50 p-4 hover:border-purple-500/30 transition-all">
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-semibold text-white text-sm leading-tight">{meeting.title}</h3>
                        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-red-900/40 text-red-400 border border-red-700/30 ml-2 whitespace-nowrap">
                          {meeting.status === 'live' ? 'LIVE' : 'SCHEDULED'}
                        </span>
                      </div>
                      <p className="text-neutral-400 text-xs mb-3 line-clamp-2">{meeting.summary}</p>
                      <div className="flex items-center gap-3 text-neutral-500 text-xs">
                        <span>{meeting.participants ?? 0} people</span>
                        <span>{meeting.duration}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="lg:col-span-2">
              <h2 className="text-xl font-bold text-gray-300 mb-4">Recent Intelligence</h2>
              {loading ? (
                <div className="text-neutral-500 text-sm">Loading...</div>
              ) : completedMeetings.length === 0 ? (
                <div className="text-neutral-600 text-sm">No completed meetings yet.</div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {completedMeetings.map((meeting) => (
                    <div key={meeting.id} className="bg-neutral-800/60 rounded-xl border border-neutral-700/50 p-4 hover:border-purple-500/30 transition-all flex flex-col gap-3">
                      <div className="flex items-start justify-between">
                        <h3 className="font-semibold text-white text-sm leading-tight flex-1">{meeting.title}</h3>
                        {meeting.sentiment && (
                          <span className={"text-xs font-medium px-2 py-0.5 rounded-full ml-2 whitespace-nowrap " + getSentimentColor(meeting.sentiment)}>
                            {meeting.sentiment}
                          </span>
                        )}
                      </div>
                      <p className="text-neutral-400 text-xs line-clamp-2">{meeting.summary}</p>
                      <div className="flex flex-col gap-2 mt-auto pt-2 border-t border-neutral-700/40">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 text-neutral-400 text-xs">
                            <span>{meeting.participants ?? 0} Attendees</span>
                            <span>•</span>
                            <span>{meeting.duration}</span>
                          </div>
                          <a
                            href={'/api/meetings/' + meeting.id + '/pdf'}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-2.5 py-1 rounded bg-purple-600/20 hover:bg-purple-600/40 border border-purple-500/40 text-xs text-purple-300 hover:text-purple-200 font-medium flex items-center gap-1 transition-all whitespace-nowrap"
                          >
                            Download PDF ↓
                          </a>
                        </div>

                        {/* Tokens & Step Breakdown */}
                        {(meeting.tokens_used !== undefined || meeting.processing_time || meeting.step_timings) && (
                          <div className="flex flex-col gap-1 text-[11px] bg-neutral-900/60 rounded-lg p-2 border border-neutral-700/30">
                            <div className="flex items-center justify-between flex-wrap gap-1">
                              {meeting.tokens_used !== undefined && (
                                <span className="text-purple-300 font-medium flex items-center gap-1">
                                  <span>⚡</span>
                                  <span>{typeof meeting.tokens_used === 'number' ? `${meeting.tokens_used.toLocaleString()} tokens` : meeting.tokens_used}</span>
                                </span>
                              )}
                              {meeting.processing_time && (
                                <span className="text-emerald-400 font-medium flex items-center gap-1 ml-auto">
                                  <span>⏱ Process Time:</span>
                                  <span>{meeting.processing_time}</span>
                                </span>
                              )}
                            </div>
                            {meeting.step_timings && (
                              <div className="text-[10px] text-neutral-400 font-mono tracking-tight pt-0.5 border-t border-neutral-800">
                                {meeting.step_timings}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>

      </main>
    </div>
  );
}
