'use client';

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
};

export default function Dashboard() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [lang, setLang] = useState('en');
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      setLang(urlParams.get('lang') || 'en');
    }
  }, []);

  const [botUrl, setBotUrl] = useState('');
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [scheduledTime, setScheduledTime] = useState('');
  const [dispatchStatus, setDispatchStatus] = useState('');
  const [uploadStatus, setUploadStatus] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    const fetchMeetings = async () => {
      try {
        const apiUrl = '/api';
        const res = await fetch(`${apiUrl}/meetings`);
        if (res.ok) {
          const data = await res.json();
          setMeetings(data);
        }
      } catch (e) {
        console.error("Failed to fetch meetings", e);
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
      const apiUrl = '/api';
      
      const endpoint = scheduledTime ? '/meeting/schedule' : '/dispatch';
      const payload = scheduledTime ? { url: botUrl, scheduled_time: new Date(scheduledTime).toISOString() } : { url: botUrl };
      
      const res = await fetch(`${apiUrl}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        setDispatchStatus(scheduledTime ? '✅ AI Notetaker Scheduled!' : '✅ AI Notetaker Dispatched!');
        setBotUrl('');
        setScheduledTime('');
      } else {
        const errorText = await res.text();
        setDispatchStatus(`❌ Error ${res.status}: ${errorText.substring(0, 50)}`);
      }
    } catch (e) {
      setDispatchStatus(`❌ Backend unreachable: ${e}`);
    }
    setTimeout(() => setDispatchStatus(''), 5000);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    
    setIsUploading(true);
    setUploadStatus('Preparing infinite upload...');
    
    const apiUrl = '/api';
    const chunkSize = 50 * 1024 * 1024; // 50MB chunks
    const totalChunks = Math.ceil(file.size / chunkSize);
    const fileId = `${Date.now()}-${file.name.replace(/[^a-zA-Z0-9.-]/g, '_')}`;
    
    try {
      for (let i = 0; i < totalChunks; i++) {
        const start = i * chunkSize;
        const end = Math.min(start + chunkSize, file.size);
        const chunk = file.slice(start, end);
        
        const formData = new FormData();
        formData.append('chunk', chunk);
        formData.append('file_id', fileId);
        formData.append('chunk_index', i.toString());
        formData.append('total_chunks', totalChunks.toString());
        formData.append('filename', file.name);
        
        setUploadStatus(`Uploading chunk ${i + 1} of ${totalChunks} (${Math.round((i/totalChunks)*100)}%)`);
        
        const res = await fetch(`${apiUrl}/upload-chunk`, {
          method: 'POST',
          body: formData,
        });
        
        if (!res.ok) {
          throw new Error(await res.text());
        }
      }
      setUploadStatus('✅ Upload complete! Processing...');
    } catch (err: any) {
      setUploadStatus(`❌ Upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
      setTimeout(() => setUploadStatus(''), 8000);
      e.target.value = '';
    }
  };

  const handleDownloadPdf = (meetingId: string) => {
    const apiUrl = '/api';
    window.open(`${apiUrl}/meeting/${meetingId}/pdf`, '_blank');
  };

  return (
    <div className="min-h-screen bg-neutral-900 text-white font-sans selection:bg-purple-500 selection:text-white">
      {/* Navigation */}
      <nav className="border-b border-neutral-800 bg-neutral-950/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-600 to-blue-500 flex items-center justify-center font-bold text-lg shadow-[0_0_15px_rgba(168,85,247,0.5)]">
                AI
              </div>
              <span className="font-semibold text-xl tracking-tight">{lang === 'zh-CN' ? '会议智能' : lang === 'zh-TW' ? '會議智能' : 'Meeting Intelligence'}</span>
            </div>
            <div className="flex items-center gap-4">
              <button className="text-neutral-400 hover:text-white transition-colors">{lang === 'zh-CN' ? '设置' : lang === 'zh-TW' ? '設定' : 'Settings'}</button>
              <div className="w-8 h-8 rounded-full bg-neutral-800 border border-neutral-700 flex items-center justify-center overflow-hidden">
                <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=CEO" alt="Profile" className="w-full h-full object-cover" />
              </div>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        {/* Dispatch Bot Section */}
        <section className="mb-12">
          <div className="bg-neutral-800/50 rounded-2xl border border-neutral-700/50 p-6 backdrop-blur-sm relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-purple-500 to-blue-500"></div>
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 relative z-10">
              <div>
                <h2 className="text-2xl font-bold text-white mb-2">{lang === 'zh-CN' ? '发送 AI 会议纪要机器人' : lang === 'zh-TW' ? '發送 AI 會議記錄機器人' : 'Send the AI Notetaker'}</h2>
                <p className="text-neutral-400">{lang === 'zh-CN' ? '在下方粘贴 Teams 链接，AI 机器人将作为访客自动加入。' : lang === 'zh-TW' ? '在下方貼上 Teams 連結，AI 機器人將作為訪客自動加入。' : 'Paste your Microsoft Teams meeting link below, and the AI bot will automatically join as a guest.'}</p>
              </div>
              <form onSubmit={handleDispatch} className="flex flex-col md:flex-row w-full md:w-auto gap-3">
                <input 
                  type="text" 
                  value={botUrl}
                  onChange={(e) => setBotUrl(e.target.value)}
                  placeholder="https://teams.microsoft.com/l/meetup-join/..." 
                  className="flex-1 md:w-80 bg-neutral-900 border border-neutral-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all placeholder:text-neutral-600"
                />
                <input 
                  type="datetime-local" 
                  value={scheduledTime}
                  onChange={(e) => setScheduledTime(e.target.value)}
                  className="bg-neutral-900 border border-neutral-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all text-sm"
                  title="Leave empty to join immediately"
                />
                <button 
                  type="submit"
                  disabled={!botUrl || dispatchStatus === 'Dispatching...'}
                  className="bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:hover:bg-purple-600 text-white px-6 py-2 rounded-lg font-medium transition-colors whitespace-nowrap shadow-[0_0_15px_rgba(147,51,234,0.3)] hover:shadow-[0_0_20px_rgba(147,51,234,0.5)]"
                >
                  {scheduledTime ? 'Schedule Bot' : 'Dispatch Bot'}
                </button>
              </form>
            </div>
            {dispatchStatus && (
              <p className="mt-4 text-sm font-medium text-purple-400 animate-pulse">{dispatchStatus}</p>
            )}
            
            
            {/* YouTube Bot Section */}
            <div className="mt-6 pt-6 border-t border-neutral-700/50 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 relative z-10">
              <div>
                <h3 className="text-xl font-bold text-white mb-2">{lang === 'zh-CN' ? '转写 YouTube 视频' : lang === 'zh-TW' ? '轉寫 YouTube 影片' : 'Transcribe YouTube Video'}</h3>
                <p className="text-neutral-400 text-sm">{lang === 'zh-CN' ? '粘贴 YouTube 链接。机器人将使用您的本地 Chrome Cookie 以绕过会员限制。' : lang === 'zh-TW' ? '貼上 YouTube 連結。機器人將使用您的本地 Chrome Cookie 以繞過會員限制。' : 'Paste a YouTube URL. The bot will use your local Chrome cookies to bypass memberships.'}</p>
              </div>
              <form onSubmit={async (e) => {
                e.preventDefault();
                if (!youtubeUrl.includes('youtube') && !youtubeUrl.includes('youtu.be')) {
                    setDispatchStatus('❌ Please enter a valid YouTube URL in the field.');
                    return;
                }
                setDispatchStatus('Dispatching YouTube Bot...');
                try {
                  const res = await fetch('/api/youtube', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: youtubeUrl })
                  });
                  if (res.ok) {
                    setDispatchStatus('✅ YouTube Notetaker Dispatched!');
                    setYoutubeUrl('');
                  } else {
                    setDispatchStatus(`❌ Error ${res.status}`);
                  }
                } catch (e) {
                  setDispatchStatus(`❌ Backend unreachable`);
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
                  className="bg-red-600 hover:bg-red-500 disabled:opacity-50 disabled:hover:bg-red-600 text-white px-6 py-2 rounded-lg font-medium transition-colors whitespace-nowrap shadow-[0_0_15px_rgba(220,38,38,0.3)] hover:shadow-[0_0_20px_rgba(220,38,38,0.5)]"
                >
                  {lang === 'zh-CN' ? '下载并转写 YouTube' : lang === 'zh-TW' ? '下載並轉寫 YouTube' : 'Download & Transcribe YouTube'}
                </button>
              </form>
            </div>

            <div className="mt-6 pt-6 border-t border-neutral-700/50 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 relative z-10">
              <div>
                <h3 className="text-xl font-bold text-white mb-2">{lang === 'zh-CN' ? '上传本地录音' : lang === 'zh-TW' ? '上傳本地录音' : 'Upload Local Recording'}</h3>
                <p className="text-neutral-400 text-sm">{lang === 'zh-CN' ? '有视频或音频文件？直接上传以进行 AI 转写和智能提取。' : lang === 'zh-TW' ? '有影片或音訊檔案？直接上傳以進行 AI 轉寫和智能提取。' : 'Have a video or audio file? Upload it directly for AI transcription and intelligence extraction.'}</p>
              </div>
              <div className="flex flex-col items-end gap-2">
                <label className={`cursor-pointer bg-neutral-900 hover:bg-neutral-800 border border-neutral-700 text-white px-6 py-2 rounded-lg font-medium transition-all shadow-sm flex items-center gap-2 ${isUploading ? 'opacity-50 pointer-events-none' : ''}`}>
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                  {isUploading ? (lang === 'zh-CN' ? '上传中...' : lang === 'zh-TW' ? '上傳中...' : 'Uploading...') : (lang === 'zh-CN' ? '选择视频/音频文件' : lang === 'zh-TW' ? '選擇影片/音訊檔案' : 'Select Video/Audio File')}
                  <input type="file" className="hidden" accept="video/*,audio/*" onChange={handleFileUpload} disabled={isUploading} />
                </label>
                {uploadStatus && (
                  <p className="text-sm font-medium text-cyan-400 animate-pulse">{uploadStatus}</p>
                )}
              </div>
            </div>
          </div>
        </section>

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Live Meetings Column */}
            <div className="lg:col-span-1 space-y-6">
              <h2 className="text-xl font-bold flex items-center gap-3">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse shadow-[0_0_10px_rgba(239,68,68,0.8)]"></span>
                {lang === 'zh-CN' ? '活跃与已排程' : lang === 'zh-TW' ? '活躍與已排程' : 'Active & Scheduled'}
              </h2>
              {meetings.filter((m) => m.status === 'live' || m.status === 'scheduled').map((meeting) => (
                <div key={meeting.id} className="relative group rounded-2xl p-[1px] overflow-hidden bg-gradient-to-b from-purple-500/30 to-transparent transition-all duration-300 hover:shadow-[0_0_30px_rgba(168,85,247,0.15)]">
                  <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                  <div className="relative bg-gray-900/90 backdrop-blur-xl p-6 rounded-2xl h-full border border-white/5">
                    <div className="flex justify-between items-start mb-4">
                      <h3 className="font-semibold text-lg">{meeting.title}</h3>
                      <span className={`px-3 py-1 text-xs font-bold rounded-full flex items-center gap-1.5 ${meeting.status === 'live' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-blue-500/10 text-blue-400 border-blue-500/20'} border`}>
                        {meeting.status === 'live' ? <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping"></span> : <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
                        {meeting.status === 'live' ? (lang === 'zh-CN' ? '实时' : lang === 'zh-TW' ? '實時' : 'LIVE') : (lang === 'zh-CN' ? '已排程' : lang === 'zh-TW' ? '已排程' : 'SCHEDULED')}
                      </span>
                    </div>
                    <p className="text-gray-400 text-sm mb-4 line-clamp-2">{meeting.summary}</p>
                    <div className="flex items-center gap-4 text-xs text-gray-500 font-medium">
                      <div className="flex items-center gap-1.5">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
                        {meeting.participants}
                      </div>
                      <div className="flex items-center gap-1.5">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        {meeting.duration}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Completed Meetings Column */}
            <div className="lg:col-span-2 space-y-6">
              <h2 className="text-xl font-bold text-gray-300">{lang === 'zh-CN' ? '最近的智能纪要' : lang === 'zh-TW' ? '最近的智能记录' : 'Recent Intelligence'}</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {meetings.filter((m) => m.status === 'completed').map((meeting) => (
                  <div key={meeting.id} className="group rounded-2xl p-[1px] bg-gradient-to-b from-white/10 to-transparent transition-all duration-300 hover:from-cyan-500/30">
                    <div className="bg-gray-900/80 backdrop-blur-sm p-6 rounded-2xl h-full border border-white/5 group-hover:bg-gray-900/60 transition-colors">
                      <div className="flex justify-between items-start mb-4">
                        <h3 className="font-semibold text-lg text-gray-100">{meeting.title}</h3>
                        <span className="px-3 py-1 text-xs font-bold rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                          {meeting.sentiment}
                        </span>
                      </div>
                      <p className="text-gray-400 text-sm mb-6 leading-relaxed line-clamp-3">{meeting.summary}</p>
                      <div className="flex items-center justify-between border-t border-white/5 pt-4 mt-auto">
                        <div className="flex items-center gap-4 text-xs text-gray-500 font-medium">
                          <span>{meeting.participants} Attendees</span>
                          <span>{meeting.duration}</span>
                        </div>
                        <button 
                          onClick={() => handleDownloadPdf(meeting.id)}
                          className="text-cyan-400 hover:text-cyan-300 text-sm font-semibold transition-colors flex items-center gap-1"
                        >
                          Download PDF <svg className="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
